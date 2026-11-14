import csv
import io
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class CustomerExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        users = get_user_model()
        self.admin = users.objects.create_user(username='export-admin', email='export-admin@example.test', role='Admin')
        self.customer = users.objects.create_user(username='customer-one', email='one@example.test', first_name='বিলাল', phone='+8801700000000')
        users.objects.create_user(username='=HYPERLINK("bad")', email='two@example.test')

    def content(self, response):
        return b''.join(response.streaming_content).decode('utf-8-sig')

    def test_list_and_exports_require_platform_staff(self):
        for path in ['/api/store/admin/customers/', '/api/store/admin/customers/export/']:
            self.assertEqual(self.client.get(path).status_code, 401)
            self.client.force_authenticate(self.customer)
            self.assertEqual(self.client.get(path).status_code, 403)
            self.client.force_authenticate(None)
        staff = get_user_model().objects.create_user(username='sub-staff', email='staff@example.test', role='Staff', domain_user_id=self.admin)
        self.client.force_authenticate(staff)
        self.assertEqual(self.client.get('/api/store/admin/customers/export/').status_code, 403)

    def test_csv_exports_all_matching_customers_not_visible_page_and_neutralizes_formulas(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/store/admin/customers/export/?file_type=csv&page=99')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertIn('.csv', response['Content-Disposition'])
        rows = list(csv.DictReader(io.StringIO(self.content(response))))
        self.assertEqual(len(rows), 2)
        self.assertTrue(any(row['username'].startswith("'=HYPERLINK") for row in rows))
        row = next(row for row in rows if row['email'] == 'one@example.test')
        self.assertEqual(row['first_name'], 'বিলাল')
        self.assertEqual(row['phone'], "'+8801700000000")
        self.assertNotIn('password', row)
        self.assertNotIn('last_ip', row)

    def test_json_preserves_values_search_and_safe_fields(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/store/admin/customers/export/?file_type=json&search=one@example.test')
        rows = json.loads(self.content(response))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['phone'], '+8801700000000')
        self.assertEqual(rows[0]['total_spent'], '0.00')
        self.assertEqual(rows[0]['order_count'], 0)
        self.assertNotIn('password', rows[0])

    def test_unknown_file_type_rejected(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/store/admin/customers/export/?file_type=xlsx').status_code, 400)
