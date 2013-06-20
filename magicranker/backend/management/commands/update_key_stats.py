from datetime import datetime
from django.core.mail import send_mail

from django.core.management.base import BaseCommand, CommandError

from magicranker.backend.scrapers import YahooFinance
from magicranker.stock.models import Detail, PriceHistory, PerShare


class Command(BaseCommand):
    help = 'Get Profile Details from YahooFinance'

    def _update_latest_price(self, stock, date, yf):
        # get today's price information
        price_data = yf.get_current_price()
        if price_data:
            code, date, price, volume = price_data
            self.stdout.write('Attempting to update {0} with {1}, {2}, {3}\n'.format(
                stock.code, str(date), price, volume))
            try:
                price_history = (
                    PriceHistory.objects.get(code=stock, date=date))
            except PriceHistory.DoesNotExist:
                price_history = None

            if price_history:
                price_history.close = price
                price_history.volume = volume
            else:
                price_history = PriceHistory(
                    code=stock, date=date, close=price, volume=volume)
            price_history.save()
            
            return True
        else:
            return False

    def _update_key_stats(self, stock, date, yf):
        # Get key statistics (relies on date collected above)
        stats_data = yf.get_key_stats()
        if stats_data:
            code, eps, roe, bv, pe, mc = stats_data
            self.stdout.write('Attempting to update {0} with {1}, {2}, {3}, {4}, {5}\n'.format(
                code, eps, roe, bv, pe, mc))

            try:
                per_share = (
                    PerShare.objects.get(code=stock, date=date))
            except PerShare.DoesNotExist:
                per_share = None

            if not per_share:
                per_share = PerShare(
                    code=stock, date=date)
            per_share.earnings = eps
            per_share.roe = roe
            per_share.book_value = bv
            per_share.pe = pe
            per_share.market_cap = mc
            per_share.save()

            self.stdout.write(
                'Updating {0} with {1}, {2}, {3}, {4}, {5}\n'.format(
                    stock.code, eps, roe, bv, pe, mc))

    def handle(self, *args, **kwargs):
        stocks = Detail.objects.filter(is_listed=True)
        scrape_count = 0
        for stock in stocks:
            yf = YahooFinance.YahooFinance(stock.code)
            date = datetime.today().date()
            if self._update_latest_price(stock, date, yf):
                self._update_key_stats(stock, date, yf)
                scrape_count += 1

        title = 'Report: key stats complete ({0})'.format(
                datetime.now())
        message = '{0} companies updated'.format(scrape_count)
        send_mail(
            title, message, 'reports@magicranker.com',
            ['lextoumbourou@gmail.com'], fail_silently = False)
