import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()


POSTS_QUANTITY_PAGE_ONE = 10
POSTS_QUANTITY_PAGE_TWO = 3
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group_one = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_two = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

    def setUp(self):
        cache.clear()
        NUMBER_OF_POSTS = 3
        self.guest_client = Client()
        self.user = self.user
        self.user2 = User.objects.create_user(username='auth2')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)
        posts = [
            Post(author=self.user, text='Тестовый постa',
                 group=self.group_one) for i in range(NUMBER_OF_POSTS)
        ]
        Post.objects.bulk_create(posts)
        Post.objects.create(author=self.user, text='Тестовый постa',
                            group=self.group_two, image=self.uploaded)
        Follow.objects.create(user=self.user, author=self.user2)

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_new_post_appears_in_subscriptions(self):
        new_post = Post.objects.create(
            author=self.user2,
            text='Тестовый',
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertContains(response, new_post.text)

    def test_new_post_does_not_appear_in_unsubscribed_users(self):
        new_post = Post.objects.create(
            author=self.user,
            text='Тестовый',
        )
        response = self.authorized_client2.get(reverse('posts:follow_index'))
        self.assertNotContains(response, new_post.text)

    def test_profile_follow(self):
        response = self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': 'auth2'}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(Follow.objects.filter(user=self.user,
                                              author=self.user2).exists())

    def test_profile_unfollow(self):
        Follow.objects.filter(user=self.user, author=self.user2).delete()
        Follow.objects.create(user=self.user, author=self.user2)
        response = self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': 'auth2'}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertFalse(Follow.objects.filter(user=self.user,
                                               author=self.user2).exists())

    def test_profile_follow_already_following(self):
        Follow.objects.filter(user=self.user, author=self.user2).delete()
        Follow.objects.create(user=self.user, author=self.user2)
        response = self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': 'auth2'}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(Follow.objects.filter(
            user=self.user,
            author=self.user2).distinct().exists())

    def test_profile_unfollow_not_following(self):
        response = self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': 'auth2'}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertFalse(Follow.objects.filter(user=self.user,
                                               author=self.user2).exists())

    def test_pages_uses_correct_template(self):
        post_id = Post.objects.latest('id').id
        templates_page_names = {
            'posts/index.html': '/',
            'posts/group_list.html': '/group/test-slug/',
            'posts/profile.html': '/profile/auth/',
            'posts/post_detail.html': f'/posts/{post_id}/',
            'posts/create_post.html': '/create/',
        }
        for template, url_path in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(url_path)
                self.assertTemplateUsed(response, template)

    def test_cache_index(self):
        response = self.guest_client.get(reverse('posts:index'))
        Post.objects.create(author=self.user,
                            text='Тестовый',
                            group=self.group_two)
        response_with_cache = self.guest_client.get(reverse('posts:index'))
        posts_cache = response_with_cache.content
        self.assertEqual(response.content, posts_cache)
        cache.clear()
        response_without_cache = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response_without_cache.content,
                            response_with_cache.content)

    def test_post_edit_use_correct_template(self):
        post_id = Post.objects.all().first().id
        template = 'posts/create_post'
        response = self.authorized_client.get(reverse(
            'posts:post_edit',
            kwargs={'post_id': f'{post_id}'}))
        self.assertTemplateNotUsed(response, template)

    def test_index_show_correct_context(self):
        response = self.guest_client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.group, Post.objects.all().first().group)
        self.assertEqual(first_object.text, Post.objects.all().first().text)
        self.assertEqual(first_object.image, Post.objects.all().first().image)

    def test_group_list_show_correct_context(self):
        response = self.guest_client.get(reverse('posts:group_posts',
                                                 kwargs={'slug': 'test-slug2'}
                                                 ))
        context_index = ['page_obj', 'group']
        first_object = response.context['page_obj'][0]
        for context_key in context_index:
            self.assertIn(context_key, response.context)
        self.assertEqual(response.context['group'],
                         Post.objects.all().first().group)
        self.assertEqual(first_object.image, Post.objects.all().first().image)

    def test_profile_show_correct_context(self):
        response = self.guest_client.get(reverse(
            'posts:profile',
            kwargs={'username': 'auth'}))
        context_profile = ['page_obj', 'count', 'author']
        first_object = response.context['page_obj'][0]
        for context_key in context_profile:
            self.assertIn(context_key, response.context)
        self.assertEqual(first_object.image, Post.objects.all().first().image)

    def test_post_detail_show_correct_context(self):
        post_id = Post.objects.all().first().id
        posts_count = self.user.posts.select_related('author').count()
        response = self.guest_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': f'{post_id}'}))
        context_post_detail = ['post', 'posts']
        object = response.context['post']
        for context_key in context_post_detail:
            self.assertIn(context_key, response.context)
        self.assertEqual(response.context['post'], Post.objects.all().first())
        self.assertEqual(response.context['posts'], posts_count)
        self.assertEqual(object.image, Post.objects.all().first().image)

    def test_post_create_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        context_post_create = ['form', 'title']
        for context_key in context_post_create:
            self.assertIn(context_key, response.context)
        self.assertEqual(response.context['title'], 'Новый пост')
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        post_id = Post.objects.all().last().id
        response = self.authorized_client.get(reverse(
            'posts:post_edit',
            kwargs={'post_id': f'{post_id}'}))
        context_post_edit = ['is_edit', 'form', 'title']
        for context_key in context_post_edit:
            self.assertIn(context_key, response.context)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        self.assertNotEqual(response.context['title'], ' ')
        self.assertEqual(response.context['title'], 'Редактировать пост')
        self.assertEqual(response.context['is_edit'], True)
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_index_page_posts_have_corect_group(self):
        response = self.guest_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.group, self.group_two)
        self.assertNotEqual(first_object.group, self.group_one)

    def test_group_list_page_posts_have_corect_group(self):
        response = self.guest_client.get(reverse('posts:group_posts',
                                                 kwargs={'slug': 'test-slug'}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.group, self.group_one)
        self.assertNotEqual(first_object.group, self.group_two)

    def test_profile_page_posts_have_corect_group(self):
        response = self.guest_client.get(reverse('posts:profile',
                                                 kwargs={'username': 'auth'}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.group, self.group_two)
        self.assertNotEqual(first_object.group, self.group_one)


class PostPaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = self.user
        posts = [
            Post(author=self.user, text='Тестовый постa',
                 group=self.group) for i in range(POSTS_QUANTITY_PAGE_ONE
                                                  + POSTS_QUANTITY_PAGE_TWO
                                                  )
        ]
        Post.objects.bulk_create(posts)

    def test_index_page_show_ten_posts(self):
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']),
                         POSTS_QUANTITY_PAGE_ONE)

    def test_index_page_show_two_post(self):
        response = self.guest_client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         POSTS_QUANTITY_PAGE_TWO)

    def test_profile_page_show_ten_post(self):
        response = self.guest_client.get(reverse(
            'posts:profile',
            kwargs={'username': 'auth'}))
        self.assertEqual(len(response.context['page_obj']),
                         POSTS_QUANTITY_PAGE_ONE)

    def test_profile_page_show_two_post(self):
        response = self.guest_client.get(reverse(
            'posts:profile',
            kwargs={'username': 'auth'}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         POSTS_QUANTITY_PAGE_TWO)

    def test_group_list_page_show_ten_post(self):
        response = self.guest_client.get(reverse(
            'posts:group_posts',
            kwargs={'slug': 'test-slug'}))
        self.assertEqual(len(response.context['page_obj']),
                         POSTS_QUANTITY_PAGE_ONE)

    def test_group_list_page_show_one_post(self):
        response = self.guest_client.get(reverse(
            'posts:group_posts',
            kwargs={'slug': 'test-slug'}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         POSTS_QUANTITY_PAGE_TWO)
