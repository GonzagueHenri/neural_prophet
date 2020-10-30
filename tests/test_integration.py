#!/usr/bin/env python3

import unittest
import os
import pathlib
import pandas as pd
import matplotlib.pyplot as plt
import logging
from neuralprophet import NeuralProphet

log = logging.getLogger("nprophet.test")
log.setLevel("WARNING")
log.parent.setLevel("WARNING")

DIR = pathlib.Path(__file__).parent.parent.absolute()
DATA_DIR = os.path.join(DIR, "example_data")
PEYTON_FILE = os.path.join(DATA_DIR, "wp_log_peyton_manning.csv")
EPOCHS = 4


class IntegrationTests(unittest.TestCase):
    plot = False

    def test_names(self):
        log.info("testing: names")
        m = NeuralProphet()
        m._validate_column_name("hello_friend")

    def test_train_eval_test(self):
        log.info("testing: Train Eval Test")
        m = NeuralProphet(
            n_lags=14,
            n_forecasts=7,
            ar_sparsity=0.1,
            epochs=EPOCHS,
        )
        df = pd.read_csv(PEYTON_FILE)
        df_train, df_test = m.split_df(df, valid_p=0.1, inputs_overbleed=True)

        metrics = m.fit(df_train, validate_each_epoch=True, valid_p=0.1,)
        val_metrics = m.test(df_test)
        log.debug("Metrics: train/eval: \n {}".format(metrics.to_string(float_format=lambda x: "{:6.3f}".format(x))))
        log.debug("Metrics: test: \n {}".format(val_metrics.to_string(float_format=lambda x: "{:6.3f}".format(x))))

    def test_trend(self):
        log.info("testing: Trend")
        df = pd.read_csv(PEYTON_FILE)
        m = NeuralProphet(
            n_changepoints=100,
            trend_smoothness=2,
            # trend_threshold=False,
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            epochs=EPOCHS,
        )
        m.fit(df,)
        future = m.make_future_dataframe(df, future_periods=60, n_historic_predictions=len(df))
        forecast = m.predict(df=future)
        if self.plot:
            m.plot(forecast)
            m.plot_components(forecast)
            m.plot_parameters()
            plt.show()

    def test_ar_net(self):
        log.info("testing: AR-Net")
        df = pd.read_csv(PEYTON_FILE)
        m = NeuralProphet(
            n_forecasts=14,
            n_lags=28,
            ar_sparsity=0.01,
            # num_hidden_layers=0,
            num_hidden_layers=2,
            # d_hidden=64,
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            epochs=EPOCHS,
        )
        m.highlight_nth_step_ahead_of_each_forecast(m.n_forecasts)
        m.fit(df, validate_each_epoch=True,)
        future = m.make_future_dataframe(df, n_historic_predictions=len(df)-m.n_lags)
        forecast = m.predict(df=future)
        if self.plot:
            m.plot_last_forecast(forecast, include_previous_forecasts=3)
            m.plot(forecast)
            m.plot_components(forecast)
            m.plot_parameters()
            plt.show()

    def test_seasons(self):
        log.info("testing: Seasonality")
        df = pd.read_csv(PEYTON_FILE)
        # m = NeuralProphet(n_lags=60, n_changepoints=10, n_forecasts=30, verbose=True)
        m = NeuralProphet(
            # n_forecasts=1,
            # n_lags=1,
            # n_changepoints=5,
            # trend_smoothness=0,
            yearly_seasonality=8,
            weekly_seasonality=4,
            # daily_seasonality=False,
            # seasonality_mode='additive',
            seasonality_mode='multiplicative',
            # seasonality_reg=10,
            epochs=EPOCHS,
        )
        m.fit(df, validate_each_epoch=True,)
        future = m.make_future_dataframe(df, n_historic_predictions=len(df), future_periods=365)
        forecast = m.predict(df=future)
        log.debug("SUM of yearly season params: {}".format(sum(abs(m.model.season_params["yearly"].data.numpy()))))
        log.debug("SUM of weekly season params: {}".format(sum(abs(m.model.season_params["weekly"].data.numpy()))))
        log.debug("season params: {}".format(m.model.season_params.items()))

        if self.plot:
            m.plot(forecast)
            m.plot_components(forecast)
            m.plot_parameters()
            plt.show()

    def test_lag_reg(self):
        log.info("testing: Lagged Regressors")
        df = pd.read_csv(PEYTON_FILE)
        m = NeuralProphet(
            n_forecasts=3,
            n_lags=5,
            ar_sparsity=0.1,
            # num_hidden_layers=2,
            # d_hidden=64,
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            epochs=EPOCHS,
        )
        if m.n_lags > 0:
            df['A'] = df['y'].rolling(7, min_periods=1).mean()
            df['B'] = df['y'].rolling(30, min_periods=1).mean()
            m = m.add_lagged_regressor(name='A')
            m = m.add_lagged_regressor(name='B', only_last_value=True)

            # m.highlight_nth_step_ahead_of_each_forecast(m.n_forecasts)
        m.fit(df, validate_each_epoch=True,)
        future = m.make_future_dataframe(df, n_historic_predictions=365)
        forecast = m.predict(future)

        if self.plot:
            # print(forecast.to_string())
            m.plot_last_forecast(forecast, include_previous_forecasts=10)
            m.plot(forecast)
            m.plot_components(forecast, figsize=(10, 30))
            m.plot_parameters(figsize=(10,30))
            plt.show()

    def test_events(self):
        log.info("testing: Events")
        df = pd.read_csv(PEYTON_FILE)
        playoffs = pd.DataFrame({
            'event': 'playoff',
            'ds': pd.to_datetime(['2008-01-13', '2009-01-03', '2010-01-16',
                                  '2010-01-24', '2010-02-07', '2011-01-08',
                                  '2013-01-12', '2014-01-12', '2014-01-19',
                                  '2014-02-02', '2015-01-11', '2016-01-17',
                                  '2016-01-24', '2016-02-07']),
        })
        superbowls = pd.DataFrame({
            'event': 'superbowl',
            'ds': pd.to_datetime(['2010-02-07', '2014-02-02', '2016-02-07']),
        })
        events_df = pd.concat((playoffs, superbowls))

        m = NeuralProphet(
            n_lags=5,
            n_forecasts=30,
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            epochs=EPOCHS,
        )
        # set event windows
        m = m.add_events(["superbowl", "playoff"], lower_window=-1, upper_window=1, mode="multiplicative", regularization=0.5)

        # add the country specific holidays
        m = m.add_country_holidays("US", mode="additive", regularization=0.5)

        history_df = m.create_df_with_events(df, events_df)
        m.fit(history_df,)

        # create the test data
        history_df = m.create_df_with_events(df.iloc[100: 500, :].reset_index(drop=True), events_df)
        future = m.make_future_dataframe(df=history_df, events_df=events_df, future_periods=30, n_historic_predictions=3)
        forecast = m.predict(df=future)
        log.debug("Event Parameters:: {}".format(m.model.event_params))
        if self.plot:
            m.plot_components(forecast, figsize=(10, 30))
            m.plot(forecast)
            m.plot_parameters(figsize=(10, 30))
            plt.show()

    def test_future_reg(self):
        log.info("testing: Future Regressors")
        df = pd.read_csv(PEYTON_FILE)
        m = NeuralProphet(
            n_forecasts=1,
            n_lags=0,
            epochs=EPOCHS,
        )

        df['A'] = df['y'].rolling(7, min_periods=1).mean()
        df['B'] = df['y'].rolling(30, min_periods=1).mean()

        m = m.add_future_regressor(name='A', regularization=0.5)
        m = m.add_future_regressor(name='B', mode="multiplicative", regularization=0.3)

        m.fit(df,)
        regressors_df = pd.DataFrame(data={'A': df['A'][:50], 'B': df['B'][:50]})
        future = m.make_future_dataframe(df=df, regressors_df=regressors_df, n_historic_predictions=10, future_periods=50)
        forecast = m.predict(df=future)

        if self.plot:
            # print(forecast.to_string())
            # m.plot_last_forecast(forecast, include_previous_forecasts=3)
            m.plot(forecast)
            m.plot_components(forecast, figsize=(10, 30))
            m.plot_parameters(figsize=(10, 30))
            plt.show()

    def test_predict(self):
        log.info("testing: Predict")
        df = pd.read_csv(PEYTON_FILE)
        m = NeuralProphet(
            n_forecasts=3,
            n_lags=5,
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            epochs=EPOCHS,
        )
        m.fit(df,)
        future = m.make_future_dataframe(df, future_periods=None, n_historic_predictions=10)
        forecast = m.predict(future)
        if self.plot:
            m.plot_last_forecast(forecast, include_previous_forecasts=10)
            m.plot(forecast)
            m.plot_components(forecast)
            m.plot_parameters()
            plt.show()

    def test_plot(self):
        log.info("testing: Plotting")
        df = pd.read_csv(PEYTON_FILE)
        m = NeuralProphet(
            n_forecasts=7,
            n_lags=14,
            # yearly_seasonality=8,
            # weekly_seasonality=4,
            epochs=EPOCHS,
        )
        m.fit(df,)
        m.highlight_nth_step_ahead_of_each_forecast(7)
        future = m.make_future_dataframe(df, n_historic_predictions=10)
        forecast = m.predict(future)
        # print(future.to_string())
        # print(forecast.to_string())
        # m.plot_last_forecast(forecast)
        m.plot(forecast)
        m.plot_components(forecast)
        m.plot_parameters()
        if self.plot:
            plt.show()

    def test_logger(self):
        # debug_logger():
        pass


def debug_logger():
    log.info("testing: Logger")
    log.setLevel("ERROR")
    log.parent.setLevel("WARNING")
    log.warning("### this WARNING should not show ###")
    log.parent.warning("this WARNING should show")
    log.error("this ERROR should show")

    log.setLevel("DEBUG")
    log.parent.setLevel("ERROR")
    log.debug("this DEBUG should show")
    log.parent.warning("### this WARNING not show ###")
    log.error("this ERROR should show")
    log.parent.error("this ERROR should show, too")
    # test existing test cases
    # test_all(log_level="DEBUG")

    # test the set_log_level function
    log.parent.setLevel("INFO")
    m = NeuralProphet(
        n_forecasts=3,
        n_lags=5,
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        log_level="DEBUG",
        epochs=EPOCHS,
    )
    log.parent.debug("this DEBUG should show")
    m.set_log_level(log_level="WARNING")
    log.parent.debug("### this DEBUG should not show ###")
    log.parent.info("### this INFO should not show ###")
