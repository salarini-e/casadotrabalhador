#!/usr/bin/env python
"""
Test script to verify the cargo field functionality
"""
import os
import sys
import django
from django.conf import settings

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'balcao_de_emprego.settings')
django.setup()

from vagas.models import Cargo
from django.test import Client
from django.urls import reverse

def test_cargo_autocomplete():
    """Test the cargo autocomplete functionality"""
    
    # Create test client
    client = Client()
    
    # Test the get_cargo view (mapped to /get_vaga/ URL)
    response = client.get('/get_vaga/', {'vaga': 'test'})
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    
    # Check if there are any cargos in the database
    cargos = Cargo.objects.all()
    print(f"Total cargos in database: {cargos.count()}")
    
    if cargos.exists():
        print("Sample cargos:")
        for cargo in cargos[:5]:
            print(f"  - {cargo.nome}")
    
    # Test with a common word
    response = client.get('/get_vaga/', {'vaga': 'ana'})
    print(f"\nTest with 'ana' - Status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")

if __name__ == '__main__':
    test_cargo_autocomplete()
