val scala3Version = "3.4.2"

lazy val root = project
  .in(file("."))
  .settings(
    name         := "agenkit-scala",
    organization := "io.agenkit",
    version      := "0.73.0",
    scalaVersion := scala3Version,
    libraryDependencies ++= Seq(
      "org.slf4j"         %  "slf4j-api"          % "2.0.9",
      "org.slf4j"         %  "slf4j-simple"        % "2.0.9"     % Test,
      "com.lihaoyi"       %% "upickle"             % "3.1.4",
      "org.scalatest"     %% "scalatest"           % "3.2.17"    % Test,
      "org.scalatestplus" %% "scalacheck-1-17"     % "3.2.17.0"  % Test,
    ),
    scalacOptions ++= Seq("-deprecation", "-feature"),
    Test / fork := true,
    Test / testOptions += Tests.Argument(TestFrameworks.ScalaTest, "-oD"),
  )
