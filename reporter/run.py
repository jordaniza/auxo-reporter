import fire
import reporter
import db_builder
import conf_generator

if __name__ == "__main__":
    fire.Fire(
        {
            "conf": conf_generator.gen,
            "build": db_builder.build,
            "report": reporter.report,
        }
    )
