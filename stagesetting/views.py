# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import logging
from django.contrib import messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.options import get_content_type_for_model
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
from .forms import CreateSettingForm, AdminFieldForm
from .utils import registry


logger = logging.getLogger(__name__)


def request_passes_test(request, obj=None):
    ok = (request.user.is_authenticated() and
          request.user.is_active and request.user.is_staff)
    if not ok:
        raise PermissionDenied("User is anonymous, inactive or is not staff")
    return ok


class CreateSetting(FormView):
    form_class = None
    template_name = 'stagesetting/create.html'
    success_url_name = 'stagesetting_update'
    admin = False
    model = None

    def get_context_data(self, **kwargs):
        ctx = super(CreateSetting, self).get_context_data(**kwargs)
        app_label = self.model._meta.app_label
        ctx.update(
            opts=self.model._meta,
            change=False,
            is_popup=(IS_POPUP_VAR in self.request.POST or
                      IS_POPUP_VAR in self.request.GET),
            save_as=False,
            has_delete_permission=self.request.user.has_perm('%s.has_delete_permission' % app_label),
            has_add_permission=self.request.user.has_perm('%s.has_add_permission' % app_label),
            show_save_and_continue=False,
            has_change_permission=self.request.user.has_perm('%s.has_change_permission' % app_label),
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
    admin = None
    model = None

    def get_context_data(self, **kwargs):
        ctx = super(UpdateSetting, self).get_context_data(**kwargs)
        app_label = self.model._meta.app_label
        ctx.update(
            opts=self.model._meta,
            add=False,
            change=True,
            is_popup=(IS_POPUP_VAR in self.request.POST or
                      IS_POPUP_VAR in self.request.GET),
            save_as=False,
            has_delete_permission=self.request.user.has_perm('%s.has_delete_permission' % app_label),
            has_add_permission=self.request.user.has_perm('%s.has_add_permission' % app_label),
            show_save_and_continue=False,
            has_change_permission=self.request.user.has_perm('%s.has_change_permission' % app_label),
            title=string_concat(_("Change "), self.object.pretty_key()),
            original=self.object,
        )
        if self.admin:
            ctx.update(
                media=self.admin.media + ctx['form'].media,
            )
        return ctx

    def get_form_class(self):
        try:
            form = registry[self.object.key]
        except KeyError as e:
            msg = 'form_class missing for setting "%(key)s"' % {
                'key': self.object.key
            }
            logger.error(msg, exc_info=1)
            raise Http404(msg)
        if self.admin:
            cls_name = str('AdminFields%s' % form.__name__)
            parents = (AdminFieldForm, form)
            replaced_form = type(form)(cls_name, parents, {})
            return replaced_form
        return form

    def get_initial(self):
        return self.object.value

    def assert_has_permission(self, request, obj=None):
        return request_passes_test(request=request, obj=obj)

    def get_object(self, *args, **kwargs):
        return get_object_or_404(self.model.objects.all(), pk=self.kwargs.get('pk'))

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.assert_has_permission(request=request, obj=self.object)
        return super(UpdateSetting, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.assert_has_permission(request=request, obj=self.object)
        return super(UpdateSetting, self).post(request, *args, **kwargs)

    def keys_changed(self, old, new):
        keys = []
        for key in new:
            if key in old and old[key] != new[key]:
                keys.append({'key': key, 'old': old[key], 'new': new[key]})
            elif key not in old:
                keys.append({'key': key, 'old': None, 'new': new[key]})
        return keys

    def form_valid(self, form):
        with transaction.atomic():
            old_value = self.object.value
            changed_data = self.keys_changed(old_value, form.cleaned_data)
            self.object.raw_value = registry.serialize(data=form.cleaned_data)
            self.object.full_clean()
            self.object.save()
            LogEntry.objects.log_action(
                user_id=self.request.user.pk,
                content_type_id=get_content_type_for_model(self.object).pk,
                object_id=self.object.pk,
                object_repr=force_text(self.object),
                action_flag=CHANGE,
                change_message="Changed %(changed)s" % {
                    'old': force_text(old_value),
                    'new': force_text(self.object.raw_value),
                    'changed': force_text(registry.serialize(changed_data))
                }
            )
        msg_dict = {'name': force_text(self.object._meta.verbose_name),
                    'obj': force_text(self.object.pretty_key())}
        msg =  _('The %(name)s "%(obj)s" was changed successfully.') % msg_dict
        messages.success(self.request, msg)
        return super(UpdateSetting, self).form_valid(form=form)


class DeleteSetting(DeleteView):
    template_name = 'stagesetting/delete.html'
    admin = False
    success_url = reverse_lazy('stagesetting_list')

    def assert_has_permission(self, request, obj=None):
        return request_passes_test(request=request, obj=obj)

    def get_context_data(self, **kwargs):
        ctx = super(DeleteSetting, self).get_context_data(**kwargs)
        ctx.update(
            opts=self.object._meta,
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
    paginate_by = 20
    template_name = 'stagesetting/list.html'
    admin = False

    def assert_has_permission(self, request):
        return request_passes_test(request=request, obj=None)

    def get(self, request, *args, **kwargs):
        self.assert_has_permission(request=request)
        return super(ListSettings, self).get(request, *args, **kwargs)


create_view = CreateSetting.as_view(model=RuntimeSetting)
delete_view = DeleteSetting.as_view(queryset=RuntimeSetting.objects.all())
update_view = UpdateSetting.as_view(model=RuntimeSetting)
list_view = ListSettings.as_view(queryset=RuntimeSetting.objects.all())
