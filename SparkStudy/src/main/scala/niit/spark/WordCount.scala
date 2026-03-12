package niit.spark

import org.apache.spark.{SparkConf, SparkContext}

/**
 * Spark WordCount程序
 * 功能：统计文本文件中每个单词出现的次数
 * 理解要点：
 * 1. SparkContext是Spark程序的入口
 * 2. RDD是弹性分布 式数据集
 * 3. flatMap: 将 一行文本拆分成单词
 * 4. map: 将每个单词映射成(单词, 1)键值对
 * 5. reduceByKey: 按键聚合，统计相同单词出现的次数
 */
object WordCount {
  def main(args: Array[String]): Unit = {
    // 1. 创建Spark配置
    val conf = new SparkConf()
      .setAppName("WordCount")
      .setMaster("local[*]")  // 本地模式运行，使用所有可用核心

    // 2. 创建SparkContext
    val sc = new SparkContext(conf)

    // 3. 设置日志级别，减少控制台输出
    sc.setLogLevel("WARN")

    try {
      // 4. 读取文件（如果参数有文件路径则使用参数，否则使用默认路径）
      val inputPath = if (args.length > 0) args(0) else "data/input.txt"
      val lines = sc.textFile(inputPath)

      // 5. 核心逻辑：单词计数
      val wordCounts = lines
        .flatMap(_.split("\\s+"))  // 按空白字符分割每一行成单词
        .map(word => (word, 1))     // 每个单词映射成(单词, 1)
        .reduceByKey(_ + _)          // 相同单词的计数相加

      // 6. 排序（按单词字母顺序）
      val sortedCounts = wordCounts.sortByKey()

      // 7. 输出结果（如果参数有输出路径则使用，否则打印到控制台）
      if (args.length > 1) {
        sortedCounts.saveAsTextFile(args(1))
        println(s"结果已保存到: ${args(1)}")
      } else {
        sortedCounts.collect().foreach(println)
      }

      // 8. 打印统计信息
      println(s"总单词数（去重前）: ${lines.flatMap(_.split("\\s+")).count()}")
      println(s"不同单词数: ${wordCounts.count()}")

    } finally {
      // 9. 关闭SparkContext
      sc.stop()
    }
  }
}