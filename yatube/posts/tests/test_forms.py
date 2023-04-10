from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from ..models import Group, Post, Comment
from django.urls import reverse
from ..forms import PostForm, CommentForm
from http import HTTPStatus
from django.conf import settings
import shutil
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTests(TestCase):
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
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.user,
            text='Тестовый постa',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'image': uploaded,
            'text': 'Тестовый постaа',
            'group': self.group.id,
        }
        response = self.authorized_client.post(reverse('posts:post_create'),
                                               data=form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, reverse('posts:profile',
                                               args=[self.post.author]))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(text='Тестовый постaа',
                                            group=self.group.id,
                                            ).exists())

    def test_edit_post(self):
        form_data = {
            'text': 'Новый текстик',
            'group': self.group.id,
        }
        response = self.authorized_client.post(reverse(
            'posts:post_edit',
            args=[self.post.id]), data=form_data)
        new_post = Post.objects.latest('id').id
        self.assertRedirects(response, reverse('posts:post_detail',
                                               args=[self.post.id]))
        self.assertNotEqual(new_post, self.post.text)

    def test_invalid_data_in_form(self):
        form_data = {
            'text': ' ',
            'group': ' '
        }
        form = PostForm(data=form_data)
        response = self.authorized_client.post(reverse('posts:post_create'),
                                               data=form_data)
        self.assertFalse(form.is_valid())
        self.assertNotEqual(response.status_code, HTTPStatus.FOUND)

    def test_invalid_data_create_guest_client(self):
        form_data = {
            'text': 'текст',
            'group': self.group.id
        }
        response = self.guest_client.post(reverse('posts:post_create'),
                                          data=form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_invalid_data_edit_guest_client(self):
        form_data = {
            'text': 'текст',
            'group': self.group.id,
        }
        response = self.guest_client.post(reverse(
            'posts:post_edit',
            args=[self.post.id]), data=form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)


class CommentFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='authh')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый постa',
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='text comment',
            post=cls.post,
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = self.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_form_comment(self):
        form_data = {
            'text': 'ugabuga'
        }
        form = CommentForm(data=form_data)
        self.assertTrue(form.is_valid())
        response = self.authorized_client.post(reverse(
            'posts:post_edit',
            args=[self.post.id]), data=form_data)
        self.assertRedirects(response, reverse('posts:post_detail',
                                               args=[self.post.id]))

    def test_comment_invalid_data(self):
        form_data = {
            'text': ' '
        }
        form = CommentForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_guest_cant_write_comment(self):
        form_data = {
            'text': 'ugabuga'
        }
        self.guest_client.post(reverse(
            'posts:post_edit',
            args=[self.post.id]), data=form_data)
        self.assertFalse(Comment.objects.filter(text='ugabuga').exists())
