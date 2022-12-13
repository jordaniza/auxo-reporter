import fire  # type: ignore
from reporter import reporter, db_builder, conf_generator

if __name__ == "__main__":
    fire.Fire(
        {
            "conf": conf_generator.gen,
            "build": db_builder.build,
            "report": reporter.report,
        }
    )
