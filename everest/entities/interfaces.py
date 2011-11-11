"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Marker interfaces for entities and aggregates.

Created on Nov 3, 2011.
"""

from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['IAggregate',
           'IEntity',
           'IRelationAggregateImplementation',
           'IRootAggregateImplementation',
           ]


# begin interfaces pylint: disable=W0232, E0213, E0211

class IEntity(Interface):
    """
    Marker interface for all entities.
    """


class IAggregate(Interface):
    """
    Marker interface for all aggregates.

    An aggregate is to an entity what a collection resource is to a member
    resource.
    """

    def create(entity_class, relation=None, ** kw):
        """
        Factory method for creating the aggregate.
        """

    def clone():
        """
        Creates a clone of this aggregate.
        """

    def count():
        """
        """

    def get_by_id(id_key):
        """
        """

    def get_by_slug(slug):
        """
        """

    def iterator():
        """
        """

    def add(entity):
        """
        """

    def remove(entity):
        """
        """


class IRootAggregateImplementation(Interface):
    """
    Marker interface for aggregate implementations.
    """


class IRelationAggregateImplementation(Interface):
    """
    Marker interface for aggregate implementations.
    """

# pylint: enable=W0232, E0213, E0211
