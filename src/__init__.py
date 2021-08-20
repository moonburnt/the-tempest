from .site import create_app
import logging

log = logging.getLogger(__name__)

# Building app from there and returning, coz thats how flask works. Weird, ik
create_app()
