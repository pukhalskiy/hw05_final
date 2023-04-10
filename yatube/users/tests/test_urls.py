from django.test import TestCase, Client
from http import HTTPStatus


class UsersURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_login_page_exist(self):
        response = self.guest_client.get('/auth/login/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_signup_page_exist(self):
        response = self.guest_client.get('/auth/signup/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_logout_page_exist(self):
        response = self.guest_client.get('/auth/logout/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_users_pages_uses_correct_templates(self):
        template_url_name = {
            '/auth/login/': 'users/login.html',
            '/auth/logout/': 'users/logged_out.html',
            '/auth/signup/': 'users/signup.html',
        }
        for url, template in template_url_name.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)
