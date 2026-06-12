# @contract: M-PAY-REPO
class M_PAY_REPO:
    def save(self):
        pass

# @contract: M-PAY-PROCESSOR
class M_PAY_PROCESSOR:
    def process(self):
        repo = M_PAY_REPO()
        repo.save()

# @contract: M-PAY-CTRL
class M_PAY_CTRL:
    def execute(self):
        processor = M_PAY_PROCESSOR()
        processor.process()

if __name__ == "__main__":
    ctrl = M_PAY_CTRL()
    ctrl.execute()
