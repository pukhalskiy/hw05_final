from django.test import TestCase, Client


class Core404Tests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_404_page_exist(self):
        response = self.guest_client.get('ugabuga')
        self.assertTemplateUsed(response, 'core/404.html')
