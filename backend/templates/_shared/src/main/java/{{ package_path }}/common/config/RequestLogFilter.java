package {{ base_package }}.common.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.concurrent.TimeUnit;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.event.Level;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.HandlerMapping;

/**
 * Writes one {@code http.request.completed} log event per request: method, route template, final
 * status and duration. Runs directly inside {@link CorrelationIdFilter} (so the event carries the
 * {@code request_id}) and outside any security filter chain (so rejections are logged with their
 * final status).
 *
 * <p>Deliberately logs only low-risk fields. The route is the matched controller pattern such as
 * {@code /api/v1/examples/{id}}; when no handler matched (rejection, 404) it is {@value
 * #UNMATCHED_ROUTE}, never the raw path, so identifiers never become log or metric labels. Query
 * strings, headers, cookies and bodies are never read, so credentials and personal data sent by
 * clients cannot reach the log.
 *
 * <p>Level: {@code ERROR} for 5xx or an escaped exception, {@code WARN} for a request slower than
 * {@code app.logging.slow-request-ms}, {@code DEBUG} for the container health probe, {@code INFO}
 * otherwise.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 1)
@Slf4j
public class RequestLogFilter extends OncePerRequestFilter {

  /** Route reported when no controller mapping matched the request. */
  static final String UNMATCHED_ROUTE = "UNMATCHED";

  private static final String HEALTH_PATH = "/actuator/health";

  private final long slowRequestMs;

  /**
   * Wires the filter; the slow-request threshold comes from {@code app.logging.slow-request-ms}.
   *
   * @param slowRequestMs requests taking at least this long are logged at WARN
   */
  public RequestLogFilter(@Value("${app.logging.slow-request-ms:2000}") long slowRequestMs) {
    this.slowRequestMs = slowRequestMs;
  }

  /** {@inheritDoc} */
  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain chain)
      throws ServletException, IOException {
    long start = System.nanoTime();
    boolean failed = false;
    try {
      chain.doFilter(request, response);
    } catch (ServletException | IOException | RuntimeException e) {
      failed = true;
      throw e;
    } finally {
      long durationMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start);
      logCompleted(request, failed ? 500 : response.getStatus(), durationMs, failed);
    }
  }

  private void logCompleted(
      HttpServletRequest request, int status, long durationMs, boolean failed) {
    Level level = levelFor(request, status, durationMs, failed);
    if (!log.isEnabledForLevel(level)) {
      return;
    }
    String route = route(request);
    log.atLevel(level)
        .addKeyValue("event.name", "http.request.completed")
        .addKeyValue("http.request.method", request.getMethod())
        .addKeyValue("http.route", route)
        .addKeyValue("http.response.status_code", status)
        .addKeyValue("duration_ms", durationMs)
        .log("{} {} {} {}ms", request.getMethod(), route, status, durationMs);
  }

  private Level levelFor(HttpServletRequest request, int status, long durationMs, boolean failed) {
    if (failed || status >= 500) {
      return Level.ERROR;
    }
    if (durationMs >= slowRequestMs) {
      return Level.WARN;
    }
    return request.getRequestURI().startsWith(HEALTH_PATH) ? Level.DEBUG : Level.INFO;
  }

  private static String route(HttpServletRequest request) {
    Object pattern = request.getAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
    return pattern == null ? UNMATCHED_ROUTE : pattern.toString();
  }
}
