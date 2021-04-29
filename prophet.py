"""doctsring for packages."""
import datetime
import logging
import pandas
from fbprophet import Prophet
from prometheus_api_client import Metric

# Set up logging
_LOGGER = logging.getLogger(__name__)


class ProphetPredictor:
    """docstring for Predictor."""

    model_name = "prophet"
    model_description = "Forecasted value from Prophet model"
    model = None
    predicted_df = None
    metric = None

    def __init__(self, metric, metric_predicted_name, rolling_data_window_size="10d", prophet_conf=None,
                 args=None):
        """Initialize the Metric object."""
        self.metric = Metric(metric, rolling_data_window_size)
        self.metric_predicted_name = metric_predicted_name
        self.prophet_conf = prophet_conf
        self.seasonality_args = args

    def train(self, metric_data=None, prediction_duration=15):
        """Train the Prophet model and store the predictions in predicted_df."""
        prediction_freq = "1MIN"
        # convert incoming metric to Metric Object
        if metric_data:
            # because the rolling_data_window_size is set, this df should not bloat
            self.metric += Metric(metric_data)

        # Don't really need to store the model, as prophet models are not retrainable
        # But storing it as an example for other models that can be retrained
        if self.prophet_conf is None:
            self.model = Prophet(
                daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True
            )
        else:
            self.model = Prophet(
                changepoint_prior_scale=self.prophet_conf["changepoint_prior_scale"],
                interval_width=self.prophet_conf["interval_width"],
                daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True
            )

        if self.seasonality_args is not None:
            self.model.add_seasonality(
                **self.seasonality_args
            )

        _LOGGER.info(
            "training data range: %s - %s", self.metric.start_time, self.metric.end_time
        )
        # _LOGGER.info("training data end time: %s", self.metric.end_time)
        _LOGGER.debug("begin training")

        self.model.fit(self.metric.metric_values)
        future = self.model.make_future_dataframe(
            periods=int(prediction_duration),
            freq=prediction_freq,
            include_history=False,
        )
        forecast = self.model.predict(future)
        forecast["timestamp"] = forecast["ds"]
        forecast = forecast[["timestamp", "yhat", "yhat_lower", "yhat_upper"]]
        forecast = forecast.set_index("timestamp")
        self.predicted_df = forecast
        _LOGGER.debug(forecast)

    def predict_value(self, prediction_datetime):
        """Return the predicted value of the metric for the prediction_datetime."""
        nearest_index = self.predicted_df.index.get_loc(
            prediction_datetime, method="nearest"
        )
        return self.predicted_df.iloc[[nearest_index]]
