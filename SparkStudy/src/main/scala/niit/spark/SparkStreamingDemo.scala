package niit.spark

import org.apache.spark.SparkConf
import org.apache.spark.streaming.{Seconds, StreamingContext}
import org.apache.spark.streaming.receiver.Receiver
import org.apache.spark.storage.StorageLevel
import scala.util.Random

/**
 * 简化版SparkStreaming示例
 * 这个版本会自己生成数据，不需要外部数据源
 */
object SimpleStreaming {

  def main(args: Array[String]): Unit = {
    // 1. 创建StreamingContext
    val conf = new SparkConf()
      .setAppName("SimpleStreaming")
      .setMaster("local[*]")

    val ssc = new StreamingContext(conf, Seconds(2))
    ssc.sparkContext.setLogLevel("WARN")
    ssc.checkpoint("data/checkpoint")

    // 2. 创建数据接收器（自动生成数据）
    val receiverStream = ssc.receiverStream(new SimpleReceiver())

    // 3. 处理数据：词频统计
    val wordCounts = receiverStream
      .flatMap(_.split("\\s+"))
      .map(word => (word, 1))
      .reduceByKey(_ + _)

    // 4. 打印结果
    wordCounts.print()

    // 5. 启动流处理
    println("=" * 50)
    println("SimpleStreaming 已启动，正在生成测试数据...")
    println("每2秒会统计一次单词出现次数")
    println("=" * 50)

    ssc.start()
    ssc.awaitTermination()
  }
}

/**
 * 自定义数据接收器
 * 作用：每秒自动生成随机单词数据
 */
class SimpleReceiver extends Receiver[String](StorageLevel.MEMORY_ONLY) {

  // 单词库
  private val words = Array("hello", "world", "spark", "scala",
    "bigdata", "hadoop", "kafka", "flink",
    "java", "python", "streaming", "batch")

  def onStart(): Unit = {
    // 在新线程中生成数据
    new Thread("数据生成器") {
      override def run(): Unit = {
        generateData()
      }
    }.start()
  }

  def onStop(): Unit = {
    // 停止时不需要额外操作
  }

  private def generateData(): Unit = {
    val rand = new Random()

    while (!isStopped()) {
      try {
        // 随机生成3-8个单词
        val count = 3 + rand.nextInt(6)
        val sentence = (1 to count)
          .map(_ => words(rand.nextInt(words.length)))
          .mkString(" ")

        // 将数据发送给Spark Streaming
        store(sentence)

        // 打印生成的数据（便于观察）
        println(s"📝 生成数据: $sentence")

        // 等待0.5-1.5秒
        Thread.sleep(500 + rand.nextInt(1000))

      } catch {
        case e: InterruptedException =>
          println("数据生成器停止")
          Thread.currentThread().interrupt()
        case e: Exception =>
          println(s"生成数据出错: ${e.getMessage}")
      }
    }
  }
}