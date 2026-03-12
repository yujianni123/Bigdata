package niit.spark

import org.apache.spark.sql.{SparkSession, Row}
import org.apache.spark.sql.types.{StructType, StructField, StringType, IntegerType, DoubleType}
import org.apache.spark.sql.functions._

/**
 * SparkSQL 示例程序
 * 功能：展示DataFrame API和SQL的使用
 */
object SparkSQLDemo {
  def main(args: Array[String]): Unit = {
    // 1. 创建SparkSession - 避免加载Hive组件
    val spark = SparkSession.builder()
      .appName("SparkSQLDemo")
      .master("local[*]")
      .config("spark.sql.warehouse.dir", "file:///tmp/spark-warehouse")
      .config("spark.sql.catalogImplementation", "in-memory")  // 避免Hive
      .config("spark.ui.enabled", "false")  // 禁用UI
      .getOrCreate()

    import spark.implicits._
    spark.sparkContext.setLogLevel("WARN")

    try {
      // 2. 创建DataFrame的几种方式

      // 方式1：从RDD转换
      println("=== 方式1：从RDD创建DataFrame ===")
      val rdd = spark.sparkContext.parallelize(Seq(
        ("张三", 25, 8500),
        ("李四", 30, 12000),
        ("王五", 28, 9500),
        ("赵六", 35, 15000)
      ))

      val df1 = rdd.toDF("name", "age", "salary")
      df1.show()

      // 方式2：使用编程方式指定Schema
      println("=== 方式2：编程方式指定Schema ===")
      val schema = StructType(Seq(
        StructField("name", StringType, nullable = false),
        StructField("age", IntegerType, nullable = true),
        StructField("salary", DoubleType, nullable = true)
      ))

      val rows = rdd.map { case (name, age, salary) =>
        Row(name, age, salary.toDouble)
      }

      val df2 = spark.createDataFrame(rows, schema)
      df2.show()

      // 方式3：读取JSON文件 - 直接从内存创建，避免文件IO问题
      println("=== 方式3：读取JSON文件 ===")
      val jsonData = Seq(
        """{"name": "张三", "age": 25, "salary": 8500, "dept": "技术部"}""",
        """{"name": "李四", "age": 30, "salary": 12000, "dept": "市场部"}""",
        """{"name": "王五", "age": 28, "salary": 9500, "dept": "技术部"}""",
        """{"name": "赵六", "age": 35, "salary": 15000, "dept": "管理部"}"""
      )

      val jsonRDD = spark.sparkContext.parallelize(jsonData)
      val df3 = spark.read.json(jsonRDD)
      df3.show()

      // 3. DataFrame API操作（DSL风格）
      println("=== DataFrame API操作 ===")

      // 选择列
      println("选择特定列：")
      df3.select("name", "salary").show()

      // 过滤
      println("过滤出工资大于10000的员工：")
      df3.filter($"salary" > 10000).show()

      // 新增列
      println("新增年薪列：")
      df3.withColumn("annual_salary", $"salary" * 12).show()

      // 聚合
      println("按部门统计平均工资：")
      df3.groupBy("dept")
        .agg(
          avg("salary").alias("avg_salary"),
          max("salary").alias("max_salary"),
          min("salary").alias("min_salary"),
          count("name").alias("emp_count")
        )
        .show()

      // 4. SQL操作
      println("=== SQL操作 ===")

      // 注册临时视图
      df3.createOrReplaceTempView("employees")

      // 执行SQL查询
      val sqlResult = spark.sql("""
        SELECT
          dept,
          COUNT(*) as emp_count,
          AVG(salary) as avg_salary,
          MAX(salary) as max_salary,
          MIN(salary) as min_salary
        FROM employees
        WHERE age >= 25
        GROUP BY dept
        ORDER BY avg_salary DESC
      """)

      println("SQL查询结果：")
      sqlResult.show()

      // 5. 复杂查询示例
      println("=== 复杂查询示例 ===")

      // 创建部门表
      val deptDF = Seq(
        ("技术部", "北京"),
        ("市场部", "上海"),
        ("管理部", "深圳")
      ).toDF("dept_name", "location")

      deptDF.createOrReplaceTempView("departments")

      // 多表关联查询
      val joinResult = spark.sql("""
        SELECT
          e.name,
          e.age,
          e.salary,
          e.dept,
          d.location
        FROM employees e
        JOIN departments d ON e.dept = d.dept_name
        WHERE e.salary > (SELECT AVG(salary) FROM employees)
        ORDER BY e.salary DESC
      """)

      println("高于平均工资的员工及其部门所在地：")
      joinResult.show()

      // 6. 窗口函数示例
      println("=== 窗口函数示例 ===")

      val windowResult = spark.sql("""
        SELECT
          name,
          dept,
          salary,
          RANK() OVER (PARTITION BY dept ORDER BY salary DESC) as dept_rank,
          AVG(salary) OVER (PARTITION BY dept) as dept_avg_salary
        FROM employees
        ORDER BY dept, dept_rank
      """)

      println("各部门员工工资排名：")
      windowResult.show()

      // 7. UDF（用户自定义函数）
      println("=== UDF示例 ===")

      // 注册UDF
      val salaryLevel = udf((salary: Double) => {
        if (salary < 9000) "初级"
        else if (salary < 12000) "中级"
        else if (salary < 15000) "高级"
        else "专家"
      })

      // 使用UDF
      val dfWithLevel = df3.withColumn("salary_level", salaryLevel($"salary"))
      dfWithLevel.select("name", "salary", "salary_level").show()

      // 8. 数据写入 - 简化写入操作，避免复杂格式
      println("=== 数据写入示例 ===")

      // 只写入简单的CSV格式
      df3.write
        .mode("overwrite")
        .option("header", "true")
        .csv("data/output/csv")

      println("CSV文件已保存到 data/output/csv")

      // 注释掉Parquet写入，如果还有问题的话
      // df3.write.mode("overwrite").parquet("data/output/parquet")
      // println("Parquet文件已保存到 data/output/parquet")

    } finally {
      // 9. 关闭SparkSession
      spark.stop()
    }
  }
}