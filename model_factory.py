import prophet
import logging

logging.basicConfig(level=logging.DEBUG)


class ModelFactory:
    def __init__(self):
        self.builders = {}

    def create(self, kind, **kwargs):
        if kind == "prophet":
            kwargs['args'] = None
            return prophet.ProphetPredictor(
                **kwargs,
            )
        elif kind == "prophet_with_seasonality":
            if 'seasonality' not in kwargs['args']:
                raise EnvironmentError("prophet_with_seasonality kind need seasonality argument to work!")
            kwargs['args'] = kwargs['args']['seasonality']
            return prophet.ProphetPredictor(
                **kwargs
            )
