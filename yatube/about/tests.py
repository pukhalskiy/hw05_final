from http import HTTPStatus

from django.test import TestCase, Client


class UsersAboutTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_author_page_exist(self):
        response = self.guest_client.get('/author/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_tech_page_exist(self):
        response = self.guest_client.get('/tech/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_about_pages_uses_correct_templates(self):
        template_url_name = {
            '/tech/': 'about/tech.html',
            '/author/': 'about/author.html',

        }
        for url, template in template_url_name.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)
