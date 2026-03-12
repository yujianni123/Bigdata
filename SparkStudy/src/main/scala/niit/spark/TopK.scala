package niit.spark

import org.apache.spark.{SparkConf, SparkContext}

/**
 * Spark TopK程 序
 * 功能：找出出现次数最多的前K个单词
 * 理解要点：
 * 1. 使用map和reduceByKey进行词频统计
 * 2. 使用sortBy按值降序排序
 * 3. 使用take方法获取前K个结果
 * 4. 展示了不同的TopK实现方式
 */
object TopK {
  def main(args: Array[String]): Unit = {
    // 默认K值
    val K = if (args.length > 1) args(1).toInt else 10

    val conf = new SparkConf()
      .setAppName(s"Top$K")
      .setMaster("local[*]")

    val sc = new SparkContext(conf)
    sc.setLogLevel("WARN")

    try {
      val inputPath = if (args.length > 0) args(0) else "data/input.txt"
      val lines = sc.textFile(inputPath)

      // 方法1：使用sortBy进行全局排序后取TopK
      println(s"=== 方法1：全局排序取Top$K ===")
      val wordCounts = lines
        .flatMap(_.split("\\s+"))
        .map(word => (word, 1))
        .reduceByKey(_ + _)

      val topKBySort = wordCounts
        .sortBy({case (_, count) => count}, ascending = false)
        .take(K)

      topKBySort.zipWithIndex.foreach { case ((word, count), index) =>
        println(s"${index + 1}. $word: $count")
      }

      // 方法2：使用takeOrdered（更高效，避免全局排序）
      println(s"\n=== 方法2：使用takeOrdered取Top$K ===")
      val topKByOrdered = wordCounts
        .takeOrdered(K)(Ordering.by[(String, Int), Int](_._2).reverse)

      topKByOrdered.zipWithIndex.foreach { case ((word, count), index) =>
        println(s"${index + 1}. $word: $count")
      }

      // 方法3：使用aggregate实现自定义聚合（适用于超大数据集）
      println(s"\n=== 方法3：使用aggregate实现TopK ===")
      val topKByAggregate = wordCounts
        .aggregate(Seq.empty[(String, Int)])(
          // 分区内合并：将新元素插入有序序列，保持TopK
          (seq, item) => (seq :+ item).sortBy(-_._2).take(K),
          // 分区间合并
          (seq1, seq2) => (seq1 ++ seq2).sortBy(-_._2).take(K)
        )

      topKByAggregate.zipWithIndex.foreach { case ((word, count), index) =>
        println(s"${index + 1}. $word: $count")
      }

      // 保存结果到文件
      if (args.length > 2) {
        val outputPath = args(2)
        sc.parallelize(topKBySort).map { case (word, count) =>
          s"$word\t$count"
        }.saveAsTextFile(outputPath)
        println(s"\n结果已保存到: $outputPath")
      }

    } finally {
      sc.stop()
    }
  }
}