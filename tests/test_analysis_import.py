import unittest
from analysis_import import prepare_import,local_proposals,validate_proposals

class AnalysisImportTests(unittest.TestCase):
    fields=[{'id':'ig','label':'Abonnés actuels Instagram'}, {'id':'fb','label':'Abonnés actuels Facebook'}]
    def source(self,text):return [{'source':'test','text':text,'uncertain':False}]
    def test_explicit_single_network(self):
        result=local_proposals(self.fields,self.source('Instagram\nAbonnés actuels : 12 450'))
        self.assertEqual([(r['id'],r['value']) for r in result],[('ig','12 450')])
    def test_new_followers_are_not_total(self):
        self.assertEqual(local_proposals(self.fields,self.source('Instagram\nNouveaux abonnés : 420')),[])
    def test_conflicting_totals_are_omitted(self):
        self.assertEqual(local_proposals(self.fields,self.source('Instagram\nAbonnés actuels : 12 450\nAbonnés actuels : 15 000')),[])
    def test_ambiguous_network_is_omitted(self):
        self.assertEqual(local_proposals(self.fields,self.source('Instagram Facebook\nAbonnés actuels : 12 450')),[])
    def test_hallucinated_or_partial_number_rejected(self):
        source=self.source('Instagram\nAbonnés actuels : 12 450')
        for value in ['450','99 000']:
            self.assertEqual(validate_proposals([{'title':'ig','angle':value,'hook':'Abonnés actuels : 12 450'}],self.fields,source),[])
    def test_unknown_field_rejected(self):
        self.assertEqual(validate_proposals([{'title':'unknown','angle':'12 450','hook':'12 450'}],self.fields,self.source('12 450')),[])
    def test_invalid_image_and_empty_data(self):
        for data in [{'images':['data:image/png;base64,YWJj'],'fields':self.fields},{'fields':self.fields},[]]:
            with self.assertRaises(ValueError):prepare_import(data)

if __name__=='__main__':unittest.main()
