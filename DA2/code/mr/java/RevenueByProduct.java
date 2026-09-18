/**
 * BCSE402L - Big Data Analytics (TH)
 * DA-2 artefact: Hadoop MapReduce job #1
 *
 * Job      : Revenue per product from olist_order_items_dataset.csv
 * Shows    : (key, value) emission, a Combiner for local aggregation,
 *            an explicit Partitioner, and Hadoop Counters for data quality.
 *
 * Input  (CSV, header row):
 *   order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value
 * Output (tab separated):
 *   product_id    total_revenue
 *
 * Mapper   : line -> (product_id, price + freight_value)      "line level"
 * Combiner : partial sum per product, inside each map task     "local aggregation"
 * Reducer  : final sum per product, in the assigned partition  "group level"
 *
 * Build:  javac -cp $(hadoop classpath) -d build RevenueByProduct.java
 * Run  :  hadoop jar build.jar RevenueByProduct /olist/raw/order_items /olist/out/revenue_by_product
 */
import java.io.IOException;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.DoubleWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Counter;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Partitioner;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.GenericOptionsParser;

public class RevenueByProduct {

    /* MapReduce counters are the standard way to surface data-quality metrics
       of a job run; they appear in the job counters summary. */
    public enum Stats {
        VALID_RECORDS,
        HEADER_RECORDS,
        MALFORMED_RECORDS,
        NON_POSITIVE_PRICE_RECORDS
    }

    /* ----------------------------- MAPPER ----------------------------- */
    public static class RevenueMapper
            extends Mapper<LongWritable, Text, Text, DoubleWritable> {

        private final Text outKey = new Text();
        private final DoubleWritable outValue = new DoubleWritable();

        /**
         * The source CSVs quote fields inconsistently: the header row quotes
         * every column, while data rows quote only the identifier columns and
         * leave numeric columns bare. A naive split(",") therefore yields keys
         * such as "\"4244733e...\"" for some rows and 4244733e... for others,
         * which splits one product across two different reducer keys.
         * Stripping the surrounding quotes normalises both forms.
         *
         * Limitation: this is not a full CSV parser, so a field containing an
         * embedded comma would still be split incorrectly. In this dataset no
         * column used by this job (product_id, price, freight_value) contains
         * an embedded comma, which is verified in the data-profile step.
         */
        private static String unquote(String s) {
            String t = s.trim();
            if (t.length() >= 2 && t.charAt(0) == '"' && t.charAt(t.length() - 1) == '"') {
                return t.substring(1, t.length() - 1).trim();
            }
            return t;
        }

        /** The header is identified by its first column rather than by a raw
         *  string prefix, because the header is a quoted row. */
        private static boolean isHeader(String[] f) {
            return f.length > 0 && "order_id".equals(unquote(f[0]));
        }

        @Override
        public void map(LongWritable key, Text value, Context ctx)
                throws IOException, InterruptedException {

            String line = value.toString().trim();
            if (line.isEmpty()) {
                return;
            }

            // -1 keeps trailing empty fields so the column count stays honest.
            String[] f = line.split(",", -1);
            if (f.length < 7) {
                ctx.getCounter(Stats.MALFORMED_RECORDS).increment(1);
                return;
            }
            if (isHeader(f)) {
                ctx.getCounter(Stats.HEADER_RECORDS).increment(1);
                return;
            }

            try {
                double price = Double.parseDouble(unquote(f[5]));
                double freight = Double.parseDouble(unquote(f[6]));

                if (price <= 0.0) {
                    ctx.getCounter(Stats.NON_POSITIVE_PRICE_RECORDS).increment(1);
                    return;
                }

                outKey.set(unquote(f[2]));                // product_id
                outValue.set(price + freight);            // line-level revenue
                ctx.getCounter(Stats.VALID_RECORDS).increment(1);
                ctx.write(outKey, outValue);

            } catch (NumberFormatException e) {
                ctx.getCounter(Stats.MALFORMED_RECORDS).increment(1);
            }
        }
    }

    /* ----------------------------- COMBINER -----------------------------
       Runs in the map task, after the map output is sorted by key and before
       the shuffle. It collapses many (product_id, amount) pairs into a single
       (product_id, partial_sum), which shrinks the volume of data written to
       local disk and transferred over the network during the shuffle.        */
    public static class RevenueCombiner
            extends Reducer<Text, DoubleWritable, Text, DoubleWritable> {

        private final DoubleWritable outValue = new DoubleWritable();

        @Override
        public void reduce(Text key, Iterable<DoubleWritable> values, Context ctx)
                throws IOException, InterruptedException {
            double partial = 0.0;
            for (DoubleWritable v : values) {
                partial += v.get();
            }
            outValue.set(partial);
            ctx.write(key, outValue);
        }
    }

    /* ----------------------------- REDUCER ----------------------------- */
    public static class RevenueReducer
            extends Reducer<Text, DoubleWritable, Text, DoubleWritable> {

        private final DoubleWritable outValue = new DoubleWritable();

        @Override
        public void reduce(Text key, Iterable<DoubleWritable> values, Context ctx)
                throws IOException, InterruptedException {
            double total = 0.0;
            for (DoubleWritable v : values) {
                total += v.get();
            }
            outValue.set(Math.round(total * 100.0) / 100.0);   // 2 decimals
            ctx.write(key, outValue);
        }
    }

    /* ---------------------------- PARTITIONER ----------------------------
       Decides which reducer owns a key. The default HashPartitioner already
       hashes the key; it is written out explicitly here to make the shuffle
       behaviour visible and to allow a custom split later (data skew).       */
    public static class ProductPartitioner extends Partitioner<Text, DoubleWritable> {
        @Override
        public int getPartition(Text key, DoubleWritable value, int numPartitions) {
            return (key.hashCode() & Integer.MAX_VALUE) % numPartitions;
        }
    }

    /* ------------------------------ DRIVER ------------------------------ */
    public static void main(String[] args) throws Exception {
        Configuration conf = new Configuration();
        String[] rest = new GenericOptionsParser(conf, args).getRemainingArgs();

        if (rest.length != 2) {
            System.err.println("Usage: RevenueByProduct <input-path> <output-path>");
            System.exit(2);
        }

        Job job = Job.getInstance(conf, "Olist: revenue per product");
        job.setJarByClass(RevenueByProduct.class);

        job.setMapperClass(RevenueMapper.class);
        job.setCombinerClass(RevenueCombiner.class);
        job.setReducerClass(RevenueReducer.class);
        job.setPartitionerClass(ProductPartitioner.class);
        job.setNumReduceTasks(3);          // three output partitions

        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(DoubleWritable.class);

        FileInputFormat.addInputPath(job, new Path(rest[0]));
        FileOutputFormat.setOutputPath(job, new Path(rest[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
