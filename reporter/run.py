import config
from reporter.run_prv import run_prv
from reporter.run_arv import run_arv


if __name__ == "__main__":
    epoch = config.main()
    run_arv(epoch)
    run_prv(epoch)
