package {{ base_package }}.common.config;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * Servlet filter that stamps every request with a correlation id for cross-log traceability.
 *
 * <p>If the caller supplies an {@code X-Correlation-ID} header it is reused (so callers can thread
 * a trace id through multiple services); otherwise a new random id is generated. The id is placed
 * in SLF4J's {@link MDC} so every log line emitted while handling the request can include it (see
 * the logging pattern in {@code application.yml}), and it is echoed back on the response header so
 * callers can correlate their own logs with the server's. Runs at {@link
 * Ordered#HIGHEST_PRECEDENCE} so the id is available to every other filter/interceptor in the
 * chain, and the MDC entry is always cleared in a {@code finally} block to avoid leaking it into
 * whatever request the servlet container's thread handles next.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class CorrelationIdFilter implements Filter {

  private static final String HEADER = "X-Correlation-ID";
  private static final String MDC_KEY = "correlationId";

  /**
   * Resolves or generates the correlation id, exposes it via MDC and the response header for the
   * duration of the request, then delegates to the rest of the filter chain.
   *
   * @param request the incoming request; expected to be an {@link HttpServletRequest}
   * @param response the outgoing response; expected to be an {@link HttpServletResponse}
   * @param chain the remaining filter chain to invoke
   * @throws IOException if an I/O error occurs during downstream filter/servlet processing
   * @throws ServletException if a servlet-related error occurs during downstream processing
   */
  @Override
  public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
      throws IOException, ServletException {
    HttpServletRequest httpRequest = (HttpServletRequest) request;
    HttpServletResponse httpResponse = (HttpServletResponse) response;
    String correlationId = httpRequest.getHeader(HEADER);
    if (correlationId == null || correlationId.isBlank()) {
      correlationId = UUID.randomUUID().toString();
    }
    try {
      MDC.put(MDC_KEY, correlationId);
      httpResponse.setHeader(HEADER, correlationId);
      chain.doFilter(request, response);
    } finally {
      MDC.clear();
    }
  }
}
