from reporter import config, rewards, writer

if __name__ == "__main__":
    epoch = config.main()
    rewards.main(epoch)
    writer.main(epoch)
