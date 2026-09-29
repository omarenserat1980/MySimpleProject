import subprocess, tempfile, unittest
from pathlib import Path
from brain_git_platform.merge import merge_branch

class MergeTests(unittest.TestCase):
    def test_fast_forward(self):
        with tempfile.TemporaryDirectory() as d:
            bare=Path(d)/"r.git"
            subprocess.run(["git","init","--bare",str(bare)],check=True,capture_output=True)
            work=Path(d)/"w"
            subprocess.run(["git","clone",str(bare),str(work)],check=True,capture_output=True)
            cfg=["-c","user.name=Brain","-c","user.email=brain@local"]
            (work/"a").write_text("one")
            subprocess.run(["git","add","a"],cwd=work,check=True)
            subprocess.run(["git",*cfg,"commit","-m","init"],cwd=work,check=True,capture_output=True)
            subprocess.run(["git","push","origin","HEAD:main"],cwd=work,check=True,capture_output=True)
            subprocess.run(["git","checkout","-b","feature"],cwd=work,check=True,capture_output=True)
            (work/"a").write_text("two")
            subprocess.run(["git","add","a"],cwd=work,check=True)
            subprocess.run(["git","*cfg","commit","-m","feature"],cwd=work,check=True,capture_output=True)
            subprocess.run(["git","push","origin","feature"],cwd=work,check=True,capture_output=True)
            subprocess.run(["git","checkout","main"],cwd=work,check=True,capture_output=True)
            subprocess.run(["git","pull"],cwd=work,check=True,capture_output=True)
            sha=merge_branch(work,"feature","main")
            self.assertEqual(sha,subprocess.run(["git","rev-parse","HEAD"],cwd=work,text=True,capture_output=True,check=True).stdout.strip())

if __name__=="__main__": unittest.main()
