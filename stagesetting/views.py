# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import logging
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin.options import IS_POPUP_VAR, \
    get_content_type_for_model
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _, string_concat
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import DeleteView
from .models import RuntimeSetting
from .forms import CreateSettingForm
from .utils import registry


logger = logging.getLogger(__name__)


def request_passes_test(request, obj=None):
    ok = (request.user.is_authenticated() and
          request.user.is_active and request.user.is_staff)
    if not ok:
        raise PermissionDenied("User is anonymous, inactive or is not staff")
    return ok


class CreateSetting(FormView):
    form_class = CreateSettingForm
    template_name = 'stagesetting/create.html'
    success_url_name = 'stagesetting_update'
    admin = False

    def get_context_data(self, **kwargs):
        ctx = super(CreateSetting, self).get_context_data(**kwargs)
        ctx.update(
            opts=RuntimeSetting._meta,
            change=False,
            is_popup=(IS_POPUP_VAR in self.request.POST or
                      IS_POPUP_VAR in self.request.GET),
            save_as=False,
            has_delete_permission=self.request.user.has_perm('stagesetting.has_delete_permission'),
            has_add_permission=self.request.user.has_perm('stagesetting.has_add_permission'),
            show_save_and_continue=False,
            has_change_permission=self.request.user.has_perm('stagesetting.has_change_permission'),
            title=_("Add new setting"),
            add=True,
        )
        return ctx

    def assert_has_permission(self, request):
        return request_passes_test(request=request)

    def get(self, request, *args, **kwargs):
        self.assert_has_permission(request=request)
        return super(CreateSetting, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.assert_has_permission(request=request)
        return super(CreateSetting, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
        return super(CreateSetting, self).form_valid(form=form)

    def get_success_url(self):
        return reverse(self.success_url_name, args=(self.object.pk,))


class UpdateSetting(FormView):
    template_name = 'stagesetting/update.html'
    success_url = reverse_lazy('stagesetting_list')
    admin = False

    def get_context_data(self, **kwargs):
        ctx = super(UpdateSetting, self).get_context_data(**kwargs)
        ctx.update(
            opts=RuntimeSetting._meta,
            change=True,
            is_popup=(IS_POPUP_VAR in self.request.POST or
                      IS_POPUP_VAR in self.request.GET),
            save_as=False,
            has_delete_permission=self.request.user.has_perm('stagesetting.has_delete_permission'),
            has_add_permission=self.request.user.has_perm('stagesetting.has_add_permission'),
            show_save_and_continue=False,
            has_change_permission=self.request.user.has_perm('stagesetting.has_change_permission'),
            title=string_concat(_("Change "), self.object.key),
            original=self.object,
        )
        return ctx

    def get_form_class(self):
        try:
            return registry[self.object.key]
        except KeyError as e:
            msg = 'form_class missing for setting "%(key)s"' % {
                'key': self.object.key
            }
            logger.error(msg, exc_info=1)
            raise Http404(msg)

    def get_initial(self):
        return self.object.raw_value

    def assert_has_permission(self, request, obj=None):
        return request_passes_test(request=request, obj=obj)

    def get_object(self, *args, **kwargs):
        return get_object_or_404(RuntimeSetting, pk=self.kwargs.get('pk'))

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.assert_has_permission(request=request, obj=self.object)
        return super(UpdateSetting, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.assert_has_permission(request=request, obj=self.object)
        return super(UpdateSetting, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            old_value = self.object.raw_value
            self.object.raw_value = form.cleaned_data
            self.object.full_clean()
            self.object.save()
            LogEntry.objects.log_action(
                user_id=self.request.user.pk,
                content_type_id=get_content_type_for_model(self.object).pk,
                object_id=self.object.pk,
                object_repr=force_text(self.object),
                action_flag=CHANGE,
                change_message="Changed %(old)r to %(new)r" % {
                    'old': old_value, 'new': self.object,
                }
            )
        return super(UpdateSetting, self).form_valid(form=form)


class DeleteSetting(DeleteView):
    queryset = RuntimeSetting.objects.all()
    template_name = 'stagesetting/delete.html'
    admin = False
    success_url = reverse_lazy('stagesetting_list')

    def assert_has_permission(self, request, obj=None):
        return request_passes_test(request=request, obj=obj)

    def get_context_data(self, **kwargs):
        ctx = super(DeleteSetting, self).get_context_data(**kwargs)
        ctx.update(
            opts=RuntimeSetting._meta,
            original=self.object,
        )
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.assert_has_permission(request=request, obj=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.assert_has_permission(request=request, obj=self.object)
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


class ListSettings(ListView):
    queryset = RuntimeSetting.objects.all()
    paginate_by = 20
    template_name = 'stagesetting/list.html'
    admin = False

    def assert_has_permission(self, request):
        return request_passes_test(request=request, obj=None)

    def get(self, request, *args, **kwargs):
        self.assert_has_permission(request=request)
        return super(ListSettings, self).get(request, *args, **kwargs)


create_view = CreateSetting.as_view()
delete_view = DeleteSetting.as_view()
update_view = UpdateSetting.as_view()
list_view = ListSettings.as_view()
