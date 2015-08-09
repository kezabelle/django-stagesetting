# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from rest_framework.fields import Field, DictField
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet
from stagesetting.models import RuntimeSetting
from stagesetting.utils import registry


class RawValueConversionField(DictField):
    def to_representation(self, value):
        if not isinstance(value, dict):
            return registry.deserialize(value)
        return super(RawValueConversionField, self).to_representation(value=value)


class RuntimeSettingSerializer(ModelSerializer):
    value = RawValueConversionField(source='raw_value')

    def validate(self, attrs):
        model = self.Meta.model()
        model.key = attrs['key']
        model.value = attrs['raw_value']
        return {'key': model.key, 'raw_value': model.raw_value}

    class Meta:
        model = RuntimeSetting
        fields = ('key', 'value')


class SettingsViewSet(ModelViewSet):
    queryset = RuntimeSetting.objects.all()
    serializer_class = RuntimeSettingSerializer
