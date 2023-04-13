from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post, NUMBER_OF_CHARACTERS_IN_POST

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый постa',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        expected_value = post.text[:NUMBER_OF_CHARACTERS_IN_POST]
        self.assertEqual(expected_value,
                         str(post.text[:NUMBER_OF_CHARACTERS_IN_POST]))

    def test_model_group_have_correct_name(self):
        group = PostModelTest.group
        expected_title = group.title
        self.assertEqual(expected_title, str(group))

    def test_group_object_have_correct_help_text(self):
        expected_value = PostModelTest.post._meta.get_field('group').help_text
        self.assertEqual(expected_value, 'Выберите группу')

    def test_author_object_have_correct_verbose_name(self):
        expected_value = PostModelTest.post._meta.get_field(
            'author').verbose_name
        self.assertEqual(expected_value, 'Автор')
