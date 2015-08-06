# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from rest_framework.fields import Field
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet
from stagesetting.models import RuntimeSetting
from stagesetting.utils import registry


class RawValueConversionField(Field):
    def to_representation(self, value):
        return registry.deserialize(value)


class RuntimeSettingSerializer(ModelSerializer):
    value = RawValueConversionField(source='raw_value', read_only=True)

    class Meta:
        model = RuntimeSetting
        fields = ('key', 'value', 'has_changed')


class SettingsViewSet(ModelViewSet):
    queryset = RuntimeSetting.objects.all()
    serializer_class = RuntimeSettingSerializer
