import tempfile, unittest, subprocess, os
from pathlib import Path
from brain_git_platform.refs import create_branch, list_refs
class RefTests(unittest.TestCase):
    def test_branch_lifecycle(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"r.git"; subprocess.run(["git","init","--bare",str(p)],check=True,capture_output=True)
            # create initial commit in a worktree
            w=Path(d)/"w"; subprocess.run(["git","clone",str(p),str(w)],check=True,capture_output=True)
            (w/"README").write_text("brain")
            subprocess.run(["git","add","README"],cwd=w,check=True)
            subprocess.run(["git","-c","user.name=Brain","-c","user.email=brain@local","commit","-m","init"],cwd=w,check=True,capture_output=True)
            subprocess.run(["git","push","origin","HEAD:main"],cwd=w,check=True,capture_output=True)
            create_branch(p,"feature/test","refs/heads/main")
            self.assertTrue(any("feature/test" in x for x in list_refs(p)))
if __name__=="__main__": unittest.main()
