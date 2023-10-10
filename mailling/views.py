import random

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import Http404
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView, TemplateView

from blog.models import Blog
from mailling.forms import MessageForm, MaillingForm
from mailling.models import Mailling, Logs, Message
from mailling.services import send_message_email, get_cache_count_mailling, get_cache_count_client


class MaillingCreateView(PermissionRequiredMixin, CreateView):
    model = Mailling
    form_class = MaillingForm
    permission_required = 'mailling.add_mailling'
    success_url = reverse_lazy('mailling:mailling_list')

    def form_valid(self, form):
        self.obj = form.save()
        self.obj.owner = self.request.user
        send_message_email(self.obj)
        self.obj.save()

        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'uid': self.request.user.id})
        return kwargs

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context['title'] = "Создание рассылки"
    #     return context


class MaillingListView(ListView):
    model = Mailling

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['object_list'] = Message.objects.filter(user=self.kwargs.get('pk'))
        context['title'] = "Список рассылок"
        return context


class MaillingDetailView(DetailView):
    model = Mailling

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Подробная информация о рассылке"
        return context


class MaillingUpdateView(PermissionRequiredMixin, UpdateView):
    model = Mailling
    form_class = MaillingForm
    permission_required = 'mailling.change_mailling'

    def get_success_url(self):
        return reverse('mailling:mailling_view', args=[self.kwargs.get('pk')])

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        if self.object.owner != self.request.user:
            raise Http404
        return self.object

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'uid': self.request.user.id})
        return kwargs


class MaillingDeleteView(PermissionRequiredMixin, DeleteView):
    model = Mailling
    success_url = reverse_lazy('mailling:mailling_list')
    permission_required = 'mailling.delete_mailling'

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        if self.object.owner != self.request.user:
            raise Http404
        return self.object


class LogsListView(ListView):
    model = Logs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Отчет проведенных рассылок"
        return context


class MessageCreateView(PermissionRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    permission_required = 'mailling.add_message'

    def get_success_url(self, *args, **kwargs):
        return reverse('mailling:mailling_list')

    def form_valid(self, form):
        self.obj = form.save()
        self.obj.owner = self.request.user
        self.obj.save()

        return super().form_valid(form)


class MessageUpdateView(PermissionRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    success_url = reverse_lazy('mailling:mailling_list')
    permission_required = 'mailling.change_message'

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        if self.object.owner != self.request.user:
            raise Http404
        return self.object


class MessageDeleteView(PermissionRequiredMixin, DeleteView):
    model = Message
    success_url = reverse_lazy('mailling:mailling_list')
    permission_required = 'mailling.delete_message'

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        if self.object.owner != self.request.user:
            raise Http404
        return self.object


class MainView(TemplateView):
    template_name = 'mailling/main.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['title'] = "Добро пожаловать в сервис управления рассылками!"

        context_data['object_list'] = random.sample(list(Blog.objects.all()), 3)
        context_data['mailling'] = get_cache_count_mailling()
        context_data['active_mailling'] = Mailling.objects.filter(status='started').count()
        context_data['client'] = get_cache_count_client()
        return context_data
