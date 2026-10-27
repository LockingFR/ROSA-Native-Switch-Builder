"""A missing/corrupt candidate cannot leave an old successful audit in place."""
from pathlib import Path
import json,subprocess,sys,tempfile,unittest
import qualify_content

class QualificationTests(unittest.TestCase):
    def test_missing_candidate_overwrites_stale_success_with_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);report=root/'report.json'
            report.write_text('{"technical_checks_passed":true}')
            r=subprocess.run([sys.executable,str(Path(qualify_content.__file__)),str(root/'missing'),str(report)],capture_output=True)
            result=json.loads(report.read_text())
            self.assertNotEqual(r.returncode,0)
            self.assertFalse(result['technical_checks_passed'])
            self.assertFalse(result['distribution_approved'])
            self.assertTrue(result['issues'])

    def test_archive_paths_stay_strict(self):
        for path in ('../outside','/root','C:/root','a\\outside'):
            self.assertFalse(qualify_content.safe(path))
        self.assertTrue(qualify_content.safe('sources/LICENSE'))

if __name__=='__main__':unittest.main()
