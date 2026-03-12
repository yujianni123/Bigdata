package niit.spark

import org.apache.spark.{SparkConf, SparkContext}
import scala.util.Random

/**
 * Spark全排序程序
 * 功能：对数据进行全排序
 * 理解要点：
 * 1. 全排序的挑战：数据分布不均匀可能导致某个分区数据过多
 * 2. 使用RangePartitioner进行范围分区，实现分布均匀的全排序
 * 3. 展示了不同排序方法的优缺点
 */
object FullSort {
  def main(args: Array[String]): Unit = {
    val conf = new SparkConf()
      .setAppName("FullSort")
      .setMaster("local[*]")

    val sc = new SparkContext(conf)
    sc.setLogLevel("WARN")

    try {
      val inputPath = if (args.length > 0) args(0) else "data/numbers.txt"

      // 方法1：简单全排序（对单词计数结果排序）
      println("=== 方法1：单词计数全排序 ===")
      val lines = sc.textFile("data/input.txt")
      val wordCounts = lines
        .flatMap(_.split("\\s+"))
        .map(word => (word, 1))
        .reduceByKey(_ + _)

      // 按计数升序排序
      val sortedByCountAsc = wordCounts.sortBy(_._2)
      println("按计数升序排序（前10个）：")
      sortedByCountAsc.take(10).foreach(println)

      // 按计数降序排序
      val sortedByCountDesc = wordCounts.sortBy(_._2, ascending = false)
      println("\n按计数降序排序（前10个）：")
      sortedByCountDesc.take(10).foreach(println)

      // 方法2：数值全排序（生成随机数进行排序）
      println("\n=== 方法2：数值全排序 ===")
      // 生成1000个随机数
      val randomNumbers = sc.parallelize(1 to 1000)
        .map(_ => Random.nextInt(10000))

      val sortedNumbers = randomNumbers.sortBy(identity)
      println("排序后的前20个随机数：")
      sortedNumbers.take(20).foreach(println)

      // 方法3：二次排序（先按第一个字段，再按第二个字段）
      println("\n=== 方法3：二次排序 ===")
      val pairs = sc.parallelize(Seq(
        (3, "apple"), (1, "banana"), (2, "apple"),
        (3, "banana"), (1, "apple"), (2, "banana")
      ))

      // 自定义排序规则：先按第一个字段升序，再按第二个字段降序
      implicit val customOrdering: Ordering[(Int, String)] =
        Ordering.Tuple2(Ordering.Int, Ordering.String.reverse)

      val sortedPairs = pairs.sortBy(identity)
      println("二次排序结果：")
      sortedPairs.collect().foreach(println)

      // 方法4：使用RangePartitioner实现高效全排序
      println("\n=== 方法4：使用RangePartitioner实现高效全排序 ===")
      val largeData = sc.parallelize(1 to 10000).map(_ => Random.nextInt(100000))

      // 先采样估算数据分布
      val sortedWithPartitioner = largeData.sortBy(identity, numPartitions = 4)

      println("数据分布情况：")
      sortedWithPartitioner.mapPartitionsWithIndex { (idx, iter) =>
        val list = iter.toList
        if (list.nonEmpty) {
          Iterator(s"分区$idx: ${list.head} 到 ${list.last}，共${list.size}个元素")
        } else {
          Iterator(s"分区$idx: 空")
        }
      }.collect().foreach(println)

      // 保存排序结果
      if (args.length > 1) {
        val outputPath = args(1)
        sortedNumbers.saveAsTextFile(outputPath + "/numbers")
        sortedByCountAsc.saveAsTextFile(outputPath + "/words_asc")
        sortedByCountDesc.saveAsTextFile(outputPath + "/words_desc")
        println(s"\n排序结果已保存到: $outputPath")
      }

    } finally {
      sc.stop()
    }
  }
}