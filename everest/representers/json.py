"""
JSON representers.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Aug 29, 2012.
"""
from __future__ import absolute_import # Makes the import below absolute
from everest.mime import JsonMime
from everest.representers.base import MappingResourceRepresenter
from everest.representers.base import RepresentationGenerator
from everest.representers.base import RepresentationParser
from everest.representers.config import RepresenterConfiguration
from everest.representers.converters import BooleanConverter
from everest.representers.converters import ConverterRegistry
from everest.representers.converters import DateTimeConverter
from everest.representers.converters import NoOpConverter
from everest.representers.dataelements import SimpleCollectionDataElement
from everest.representers.dataelements import SimpleLinkedDataElement
from everest.representers.dataelements import SimpleMemberDataElement
from everest.representers.mapping import SimpleMappingRegistry
from everest.representers.traversal import DataElementTreeTraverser
from everest.representers.traversal import PROCESSING_DIRECTIONS
from everest.representers.traversal import ResourceDataTreeTraverser
from everest.representers.traversal import ResourceDataVisitor
from everest.representers.traversal import \
                                DataElementBuilderRepresentationDataVisitor
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.utils import get_member_class
from everest.resources.utils import get_resource_class_for_relation
from everest.resources.utils import is_resource_url
from json import dumps
from json import loads
import datetime

__docformat__ = 'reStructuredText en'
__all__ = ['JsonCollectionDataElement',
           'JsonLinkedDataElement',
           'JsonMappingRegistry',
           'JsonMemberDataElement',
           'JsonRepresentationGenerator',
           'JsonRepresentationParser',
           'JsonRepresenterConfiguration',
           'JsonResourceRepresenter',
           ]


class JsonConverterRegistry(ConverterRegistry):
    pass

JsonConverterRegistry.register(datetime.datetime, DateTimeConverter)
JsonConverterRegistry.register(bool, BooleanConverter)
JsonConverterRegistry.register(int, NoOpConverter)
JsonConverterRegistry.register(float, NoOpConverter)


class JsonDataTreeTraverser(ResourceDataTreeTraverser):
    """
    Specialized traverser that extracts resource data from a tree of JSON data.
    """
    def __init__(self, root, mapping,
                 direction=PROCESSING_DIRECTIONS.READ):
        ResourceDataTreeTraverser.__init__(self, root, mapping, direction)

    def _dispatch(self, attr_key, attr, node, parent_data, visitor):
        if isinstance(node, dict):
            traverse_fn = self._traverse_member
        elif isinstance(node, list):
            traverse_fn = self._traverse_collection
        else:
            if not isinstance(node, basestring):
                raise ValueError('Need dict (member), list (collection) '
                                 'or string (URL) type for JSON data, found '
                                 '"%s"' % type(node))
            if attr.kind == ResourceAttributeKinds.MEMBER:
                traverse_fn = self._traverse_member
            elif attr.kind == ResourceAttributeKinds.COLLECTION:
                traverse_fn = self._traverse_collection
        traverse_fn(attr_key, attr, node, parent_data, visitor)

    def _get_node_type(self, node):
        relation = node.get('__jsonclass__')
        if not relation is None:
            tpe = get_resource_class_for_relation(relation)
        else:
            # In the absence of class hinting, the best we can do is to
            # look up the member class for the mapped class. For polymorphic
            # types, this will only work if a representer was initialized
            # for every derived class separately.
            tpe = get_member_class(self._mapping.mapped_class)
        return tpe

    def _get_node_terminal(self, node, attr):
        return node.get(attr.repr_name)

    def _get_node_nested(self, node, attr):
        nested_data = node.get(attr.repr_name)
        if isinstance(nested_data, dict): # Can also be None or a URL.
            json_class = nested_data.pop('__jsonclass__', None)
            if not json_class is None:
                rel = get_member_class(attr.value_type).relation
                if json_class != rel:
                    raise ValueError('Expected data for %s, got %s.'
                                     % (rel, json_class))
        return nested_data

    def _get_node_members(self, node):
        return node

    def _is_link_node(self, node, attr): # pylint: disable=W0613
        return isinstance(node, basestring) and is_resource_url(node)


class JsonRepresentationParser(RepresentationParser):
    def run(self):
        json_data = loads(self._stream.read())
        trv = JsonDataTreeTraverser(json_data, self._mapping)
        vst = DataElementBuilderRepresentationDataVisitor(self._mapping)
        trv.run(vst)
        return vst.data_element


class JsonDataElementTreeVisitor(ResourceDataVisitor):
    """
    Visitor creating JSON representations from data element nodes. 
    """
    def __init__(self):
        ResourceDataVisitor.__init__(self)
        self.__json_data = None

    def visit_member(self, attribute_key, attribute, member_node, member_data,
                     is_link_node, parent_data, index=None):
        if is_link_node:
            mb_data = member_node.get_url()
        else:
            mb_data = {}
            for attr, value in member_data.iteritems():
#                if attr.kind == ResourceAttributeKinds.TERMINAL:
                mb_data[attr.repr_name] = value
            # Use the relation for class hinting.
            mb_cls = member_node.mapping.mapped_class
            mb_data['__jsonclass__'] = mb_cls.relation
        if not index is None:
            parent_data[index] = mb_data
        elif len(attribute_key) == 0:
            self.__json_data = mb_data
        else:
            parent_data[attribute] = mb_data

    def visit_collection(self, attribute_key, attribute, collection_node,
                         collection_data, is_link_node, parent_data):
        if is_link_node:
            coll_data = collection_node.get_url()
        else:
            coll_data = \
                [mb_data[1] for mb_data in sorted(collection_data.items())]
        if len(attribute_key) == 0:
            self.__json_data = coll_data
        else:
            parent_data[attribute] = coll_data

    @property
    def json_data(self):
        return self.__json_data


class JsonRepresentationGenerator(RepresentationGenerator):
    """
    A JSON generator for resource data.
    """

    def run(self, data_element):
        trv = DataElementTreeTraverser(data_element, self._mapping,
                                       direction=PROCESSING_DIRECTIONS.WRITE)
        vst = JsonDataElementTreeVisitor()
        trv.run(vst)
        rpr_string = dumps(vst.json_data)
        self._stream.write(rpr_string)


class JsonResourceRepresenter(MappingResourceRepresenter):

    content_type = JsonMime

    @classmethod
    def make_mapping_registry(cls):
        return JsonMappingRegistry()

    def _make_representation_parser(self, stream, resource_class, mapping):
        parser = JsonRepresentationParser(stream, resource_class, mapping)
        return parser

    def _make_representation_generator(self, stream, resource_class, mapping):
        generator = JsonRepresentationGenerator(stream, resource_class, mapping)
        return generator


class JsonMemberDataElement(SimpleMemberDataElement):
    converter_registry = JsonConverterRegistry


class JsonCollectionDataElement(SimpleCollectionDataElement):
    pass


class JsonLinkedDataElement(SimpleLinkedDataElement):
    pass


class JsonRepresenterConfiguration(RepresenterConfiguration):
    pass


class JsonMappingRegistry(SimpleMappingRegistry):
    """
    Registry for JSON mappings.
    """
    member_data_element_base_class = JsonMemberDataElement
    collection_data_element_base_class = JsonCollectionDataElement
    linked_data_element_base_class = JsonLinkedDataElement
    configuration_class = JsonRepresenterConfiguration
