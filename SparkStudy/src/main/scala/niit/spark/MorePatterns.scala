package niit.spark

import org.apache.spark.{SparkConf, SparkContext}

/**
 * 更多MapRed uce设计模式
 * 功能：展示多种数据处理模式
 * 理解要点：
 * 1. 倒排索引：从文档到单词的映射反转
 * 2. 分组聚合：按维度分组统计
 * 3. 连接操作：不同类型数据的关联
 * 4. 去重计数： 计算唯一值
 * 5. 移动平均：时间序列数据处理
 */
object MorePatterns {
  def main(args: Array[String]): Unit = {
    val conf = new SparkConf()
      .setAppName("MorePatterns")
      .setMaster("local[*]")

    val sc = new SparkContext(conf)
    sc.setLogLevel("WARN")

    try {
      // 1. 倒排索引
      println("=== 模式1：倒排索引（单词到文档的映射）===")
      val documents = sc.parallelize(Seq(
        ("doc1", "hello world hello spark"),
        ("doc2", "hello scala world"),
        ("doc3", "spark is awesome")
      ))

      val invertedIndex = documents
        .flatMap { case (docId, content) =>
          content.split("\\s+").map(word => (word, docId))
        }
        .distinct()  // 一个文档中相同单词只记录一次
        .groupByKey()
        .mapValues(_.toList.sorted)
        .sortByKey()

      println("倒排索引结果：")
      invertedIndex.collect().foreach { case (word, docs) =>
        println(s"$word: ${docs.mkString(", ")}")
      }

      // 2. 分组聚合（统计每类商品的总销售额）
      println("\n=== 模式2：分组聚合 ===")
      val sales = sc.parallelize(Seq(
        ("电子产品", "iPhone", 8000),
        ("电子产品", "MacBook", 12000),
        ("服装", "T恤", 200),
        ("服装", "牛仔裤", 500),
        ("电子产品", "iPad", 4000),
        ("食品", "巧克力", 50)
      ))

      val categorySales = sales
        .map { case (category, product, amount) => (category, amount) }
        .aggregateByKey(0.0)(_ + _, _ + _)
        .sortBy(-_._2)

      println("各类别销售总额：")
      categorySales.collect().foreach { case (category, total) =>
        println(s"$category: ¥$total")
      }

      // 3. 连接操作（用户信息和订单信息关联）
      println("\n=== 模式3：连接操作 ===")
      val users = sc.parallelize(Seq(
        (1, "张三", 25),
        (2, "李四", 30),
        (3, "王五", 28)
      ))

      val orders = sc.parallelize(Seq(
        (1, "订单A", 500),
        (2, "订单B", 300),
        (1, "订单C", 200),
        (4, "订单D", 100)  // 用户ID不存在
      ))

      // 转换为键值对格式
      val userPairs = users.map { case (uid, name, age) => (uid, (name, age)) }
      val orderPairs = orders.map { case (uid, order, amount) => (uid, (order, amount)) }

      // 内连接
      val innerJoin = userPairs.join(orderPairs)
      println("内连接结果（只有双方都存在的记录）：")
      innerJoin.collect().foreach { case (uid, ((name, age), (order, amount))) =>
        println(s"用户$uid: $name ${age}岁 -> $order ¥$amount")
      }

      // 左外连接
      val leftJoin = userPairs.leftOuterJoin(orderPairs)
      println("\n左外连接结果（保留所有用户）：")
      leftJoin.collect().foreach { case (uid, ((name, age), orderOpt)) =>
        orderOpt match {
          case Some((order, amount)) =>
            println(s"用户$uid: $name ${age}岁 -> $order ¥$amount")
          case None =>
            println(s"用户$uid: $name ${age}岁 -> 无订单")
        }
      }

      // 4. 去重计数（UV计算）
      println("\n=== 模式4：去重计数（计算独立访客）===")
      val pageViews = sc.parallelize(Seq(
        ("/home", "user1"),
        ("/products", "user2"),
        ("/home", "user1"),
        ("/about", "user3"),
        ("/products", "user1"),
        ("/home", "user2")
      ))

      val uvByPage = pageViews
        .map { case (page, user) => (page, user) }
        .distinct()
        .groupByKey()
        .mapValues(_.size)
        .sortBy(-_._2)

      println("各页面独立访客数：")
      uvByPage.collect().foreach { case (page, uv) =>
        println(s"$page: $uv 人")
      }

      // 5. 移动平均（时间序列数据处理）
      println("\n=== 模式5：移动平均（窗口大小为3）===")
      val timeSeries = sc.parallelize(Seq(
        (1, 10.0), (2, 12.0), (3, 15.0),
        (4, 13.0), (5, 18.0), (6, 20.0)
      )).sortByKey()

      val windowSize = 3
      val movingAvg = timeSeries
        .collect()
        .sliding(windowSize)
        .map { window =>
          val avg = window.map(_._2).sum / windowSize
          (window.last._1, avg)
        }
        .toSeq

      println("移动平均结果：")
      movingAvg.foreach { case (time, avg) =>
        println(s"时间$time: 平均值 $avg")
      }

      // 6. 词频统计（带停用词过滤）
      println("\n=== 模式6：词频统计（过滤停用词）===")
      val stopWords = Set("the", "is", "at", "which", "on", "a", "an")
      val text = sc.parallelize(Seq(
        "The cat is on the table",
        "A dog is in the house",
        "Which book is on the desk"
      ))

      val filteredWordCount = text
        .flatMap(_.toLowerCase.split("\\s+"))
        .filter(word => !stopWords.contains(word))
        .map(word => (word, 1))
        .reduceByKey(_ + _)
        .sortBy(-_._2)

      println("过滤停用词后的词频统计：")
      filteredWordCount.collect().foreach { case (word, count) =>
        println(s"$word: $count")
      }

      // 7. 最长单词统计
      println("\n=== 模式7：最长单词统计 ===")
      val sentences = sc.parallelize(Seq(
        "Spark is a fast and general-purpose cluster computing system",
        "It provides high-level APIs in Java Scala Python and R",
        "Spark can run on Hadoop Mesos standalone or in the cloud"
      ))

      val longestWord = sentences
        .flatMap(_.split("\\s+"))
        .map(word => (word.length, word))
        .sortByKey(ascending = false)
        .first()

      println(s"最长单词: ${longestWord._2} (长度: ${longestWord._1})")

      // 8. 平均值计算
      println("\n=== 模式8：平均值计算 ===")
      val scores = sc.parallelize(Seq(
        ("语文", 85), ("数学", 92), ("英语", 78),
        ("物理", 88), ("化学", 95), ("生物", 82)
      ))

      val averageScore = scores
        .map(_._2)
        .mean()

      println(s"平均分: $averageScore")

      val subjectAverages = scores
        .groupByKey()
        .mapValues(scores => scores.sum.toDouble / scores.size)

      println("各科平均分（虽然只有一次数据）：")
      subjectAverages.collect().foreach(println)

    } finally {
      sc.stop()
    }
  }
}