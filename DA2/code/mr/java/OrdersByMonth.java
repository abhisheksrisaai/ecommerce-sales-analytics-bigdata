/**
 * BCSE402L - Big Data Analytics (TH)
 * DA-2 artefact: Hadoop MapReduce job #2
 *
 * Job      : Monthly order volume, used as the MapReduce stage of preprocessing.
 * Shows    : cleaning inside the mapper (timestamp parsing, status filtering,
 *            null handling) and a count aggregation with a Combiner.
 *
 * Input  (CSV, header row):
 *   order_id,customer_id,order_status,order_purchase_timestamp,
 *   order_approved_at,order_delivered_carrier_date,order_delivered_customer_date,
 *   order_estimated_delivery_date
 *
 * Output (tab separated):
 *   yyyy-MM    order_count
 *
 * Build:  javac -cp $(hadoop classpath) -d build OrdersByMonth.java
 * Run  :  hadoop jar build.jar OrdersByMonth /olist/raw/orders /olist/out/orders_by_month
 */
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.GenericOptionsParser;

public class OrdersByMonth {

    public enum Stats {
        VALID_ORDERS,
        HEADER_RECORDS,
        MALFORMED_RECORDS,
        NON_DELIVERED_ORDERS,
        MISSING_TIMESTAMP_RECORDS
    }

    /* The delimiter inside the CSV is a comma, but no field in this file
       contains an embedded comma, so index-based splitting is used. The
       timestamp column position is fixed by the source schema.              */
    private static final int COL_STATUS = 2;
    private static final int COL_PURCHASE_TIMESTAMP = 3;
    private static final int EXPECTED_FIELDS = 8;

    public static class OrdersByMonthMapper
            extends Mapper<LongWritable, Text, Text, IntWritable> {

        private static final IntWritable ONE = new IntWritable(1);
        /* SimpleDateFormat is not thread safe, so each map task gets its own
           instance through the map object rather than a static field. */
        private final SimpleDateFormat inFmt =
                new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        private final SimpleDateFormat outFmt = new SimpleDateFormat("yyyy-MM");
        private final Text outKey = new Text();

        /** See RevenueByProduct for why quotes must be stripped: the source
         *  files quote the header fully and data rows only selectively. */
        private static String unquote(String s) {
            String t = s.trim();
            if (t.length() >= 2 && t.charAt(0) == '"' && t.charAt(t.length() - 1) == '"') {
                return t.substring(1, t.length() - 1).trim();
            }
            return t;
        }

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

            String[] f = line.split(",", -1);
            if (f.length < EXPECTED_FIELDS) {
                ctx.getCounter(Stats.MALFORMED_RECORDS).increment(1);
                return;
            }
            if (isHeader(f)) {
                ctx.getCounter(Stats.HEADER_RECORDS).increment(1);
                return;
            }

            // Cleaning rule 1: keep only orders that actually completed.
            if (!"delivered".equals(unquote(f[COL_STATUS]))) {
                ctx.getCounter(Stats.NON_DELIVERED_ORDERS).increment(1);
                return;
            }

            // Cleaning rule 2: drop rows with a missing / unparseable timestamp.
            String ts = unquote(f[COL_PURCHASE_TIMESTAMP]);
            if (ts.isEmpty() || "\\N".equals(ts)) {
                ctx.getCounter(Stats.MISSING_TIMESTAMP_RECORDS).increment(1);
                return;
            }

            try {
                Date purchase = inFmt.parse(ts);
                outKey.set(outFmt.format(purchase));       // yyyy-MM
                ctx.getCounter(Stats.VALID_ORDERS).increment(1);
                ctx.write(outKey, ONE);
            } catch (java.text.ParseException e) {
                ctx.getCounter(Stats.MALFORMED_RECORDS).increment(1);
            }
        }
    }

    public static class SumCombiner
            extends Reducer<Text, IntWritable, Text, IntWritable> {
        private final IntWritable outValue = new IntWritable();

        @Override
        public void reduce(Text key, Iterable<IntWritable> values, Context ctx)
                throws IOException, InterruptedException {
            int sum = 0;
            for (IntWritable v : values) {
                sum += v.get();
            }
            outValue.set(sum);
            ctx.write(key, outValue);
        }
    }

    public static class SumReducer
            extends Reducer<Text, IntWritable, Text, IntWritable> {
        private final IntWritable outValue = new IntWritable();

        @Override
        public void reduce(Text key, Iterable<IntWritable> values, Context ctx)
                throws IOException, InterruptedException {
            int sum = 0;
            for (IntWritable v : values) {
                sum += v.get();
            }
            outValue.set(sum);
            ctx.write(key, outValue);
        }
    }

    public static void main(String[] args) throws Exception {
        Configuration conf = new Configuration();
        String[] rest = new GenericOptionsParser(conf, args).getRemainingArgs();

        if (rest.length != 2) {
            System.err.println("Usage: OrdersByMonth <input-path> <output-path>");
            System.exit(2);
        }

        Job job = Job.getInstance(conf, "Olist: monthly order volume");
        job.setJarByClass(OrdersByMonth.class);

        job.setMapperClass(OrdersByMonthMapper.class);
        job.setCombinerClass(SumCombiner.class);
        job.setReducerClass(SumReducer.class);
        job.setNumReduceTasks(1);

        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(IntWritable.class);

        FileInputFormat.addInputPath(job, new Path(rest[0]));
        FileOutputFormat.setOutputPath(job, new Path(rest[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
