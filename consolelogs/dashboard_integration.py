from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import types


def dashboard_page(*args, **kwargs):
    def decorator(func: typing.Callable):
        func.__dashboard_decorator_params__ = (args, kwargs)
        return func

    return decorator


class DashboardIntegration:
    bot: Red
    tracebacks = []

    @commands.Cog.listener()
    async def on_dashboard_cog_add(self, dashboard_cog: commands.Cog) -> None:
        if hasattr(self, "settings") and hasattr(self.settings, "commands_added"):
            await self.settings.commands_added.wait()
        try:
            from dashboard.rpc.thirdparties import dashboard_page
        except (
            ImportError
        ):  # Should never happen because the event would not be dispatched by the Dashboard cog.
            return
        for attr in dir(self):
            if hasattr((func := getattr(self, attr)), "__dashboard_decorator_params__"):
                setattr(
                    self,
                    attr,
                    types.MethodType(
                        dashboard_page(
                            *func.__dashboard_decorator_params__[0],
                            **func.__dashboard_decorator_params__[1],
                        )(func.__func__),
                        func.__self__,
                    ),
                )
        dashboard_cog.rpc.third_parties_handler.add_third_party(self)

    @dashboard_page(name=None)
    async def rpc_callback(self, user: discord.User, **kwargs) -> dict:
        if user.id not in self.bot.owner_ids:
            return {"status": 1, "error_message": "You're not a bot owner!"}
        console_logs = self.console_logs
        if not console_logs:
            return {"status": 0, "web-content": web_content_without_results}
        console_logs = [
            console_log.__str__(with_ansi=False, with_extra_break_line=True)
            for console_log in console_logs
        ]
        return {"status": 0, "web-content": web_content, "items": console_logs}


web_content_without_results = """
{% extends "base-site.html" %}

{% block title %} {{ _('ConsoleLogs cog') }} {% endblock title %}

{% block stylesheets %}
<link rel="stylesheet" href="//cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/default.min.css"></link>
{% endblock stylesheets %}

{% block content %}
<h2>ConsoleLogs Cog</h2>
<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-body">
                <h>No console logs on the console.</h3>
            </div>
        </div>
    </div>
</div>
{% endblock content %}
"""

web_content = """
{% extends "base-site.html" %}

{% block title %} {{ _('ConsoleLogs cog') }} {% endblock title %}

{% block stylesheets %}
<link rel="stylesheet" href="//cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/default.min.css"></link>
{% endblock stylesheets %}

{% block content %}
<h2>ConsoleLogs Cog</h2>
<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-body">
                <ul id="menu"></ul>
                <button class="btn" id="prev-button">Prev</button>
                <span id="page-info"></span>
                <button class="btn" id="next-button">Next</button>
            </div>
        </div>
    </div>
</div>
{% endblock content %}

{% block javascripts %}
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="//cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', (event) => {
        document.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightBlock(block);
        });
    });
</script>
<script>
    $(document).ready(function() {
        var items = {{ items|tojson }};
        var currentIndex = items.length - 1;
        var pageSize = 1;
        var numPages = Math.ceil(items.length / pageSize);
        function displayMenu() {
            var startIndex = currentIndex * pageSize;
            var endIndex = startIndex + pageSize;
            var visibleItems = items.slice(startIndex, endIndex);
            $('#menu').empty();
            for (var i = 0; i < visibleItems.length; i++) {
                var item = visibleItems[i];
                $('#menu').append('<pre><code class="language-python">' + hljs.highlight('python', item).value + '</code></pre>');
            }
        }
        function displayPageInfo() {
            var currentPage = currentIndex + 1;
            $('#page-info').text('Page ' + currentPage + ' of ' + numPages);
        }
        $('#prev-button').click(function() {
            if (currentIndex > 0) {
                currentIndex--;
                displayMenu();
                displayPageInfo();
            }
        });
        $('#next-button').click(function() {
            if (currentIndex < numPages - 1) {
                currentIndex++;
                displayMenu();
                displayPageInfo();
            }
        });
        displayMenu();
        displayPageInfo();
    });
</script>
{% endblock javascripts %}
"""
