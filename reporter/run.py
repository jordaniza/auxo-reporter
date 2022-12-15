import fire  # type: ignore
from reporter import conf_generator, rewards, writer


def main():
    epoch = conf_generator.main()
    rewards.main(epoch)
    writer.main(epoch)


if __name__ == "__main__":
    fire.Fire(
        {
            "conf": conf_generator.main,
            "build": rewards.main,
            "report": writer.main,
            "all": main,
        }
    )
