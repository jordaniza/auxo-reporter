import fire  # type: ignore
from reporter import config, rewards, writer


def main():
    epoch = config.main()
    rewards.main(epoch)
    writer.main(epoch)


if __name__ == "__main__":
    fire.Fire(
        {
            "conf": config.main,
            "build": rewards.main,
            "report": writer.main,
            "all": main,
        }
    )
