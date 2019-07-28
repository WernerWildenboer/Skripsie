"""
This file contains unit tests for main.py
"""
import os
from py2neo import Graph, NodeMatcher, Node, Relationship
from sys import path
from pytest import raises
import numpy as np


try:
    # Add the path relative to the root directory.
    # This lets you run tests from the project root,
    # and therefore allows CI to work properly
    path.append('./app')
    from __init__ import neo4j_connect

except ImportError:
    # If that fails it's probably because
    # you are trying to run the tests from the tests directory,
    # and so import relative to the tests directory
    path.append('../src')
    from __init__ import neo4j_connect


def test_neo4j_connect_add():
    """
    Test the neo4j_connect function in __init__.py
    and if a node and relationship can be created.
    """
    neo4j_bolt = os.environ["NEO4J_BOLT"] if "NEO4J_BOLT" in os.environ else 'bolt://localhost:7687'
    neo4j_usrname = os.environ["NEO4J_USERNAME"] if "NEO4J_USERNAME" in os.environ else 'neo4j'
    neo4j_password = os.environ["NEO4J_PASSWORD"] if "NEO4J_PASSWORD" in os.environ else 'skripsie'

    graph_init = neo4j_connect(neo4j_bolt, neo4j_usrname,
                               neo4j_password)
    tx = graph_init.begin()
    a = Node("Test", name="TN1")
    tx.create(a)
    b = Node("Test", name="TN2")
    ab = Relationship(a, "REL_TEST", b)
    tx.create(ab)
    tx.commit()
    boolean_test = graph_init.exists(ab)
    # Assertions
    assert boolean_test, "Could not connect to Neo4j."


def test_neo4j_connect_delete():
    """
    Test the neo4j_connect function in __init__.py
    and if a node and relationship can be deleted .
    """
    neo4j_bolt = os.environ["NEO4J_BOLT"] if "NEO4J_BOLT" in os.environ else 'bolt://localhost:7687'
    neo4j_usrname = os.environ["NEO4J_USERNAME"] if "NEO4J_USERNAME" in os.environ else 'neo4j'
    neo4j_password = os.environ["NEO4J_PASSWORD"] if "NEO4J_PASSWORD" in os.environ else 'skripsie'

    graph_init = neo4j_connect(neo4j_bolt, neo4j_usrname,
                               neo4j_password)

    graph_init.run(
        "MATCH (a)-[x:REL_TEST]-(b) WHERE a.name = 'TN1' AND b.name = 'TN2' DELETE a,b,x")

    list_test = graph_init.run(
        "MATCH (a)-[x:REL_TEST]-(b) WHERE a.name = 'TN1' AND b.name = 'TN2' RETURN a,b,x").to_ndarray()

    # Assertions
    assert not list_test, "Could not connect to Neo4j."
