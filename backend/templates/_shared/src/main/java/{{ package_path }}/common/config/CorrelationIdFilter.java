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
import java.util.regex.Pattern;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * Servlet filter that stamps every request with a request id for cross-log traceability.
 *
 * <p>If the caller supplies an {@code X-Correlation-ID} header that is 1-64 characters of {@code
 * [A-Za-z0-9._-]} it is reused (so callers can thread an id through multiple services); a missing
 * or malformed value (too long, spaces, CR/LF or other control characters that could forge log
 * lines) is replaced by a new random id, because the header is untrusted input. The id is placed in
 * SLF4J's {@link MDC} under {@value #MDC_KEY} so every log line emitted while handling the request
 * can include it, and it is echoed back on the response header so callers can correlate their own
 * logs with the server's. Runs at {@link Ordered#HIGHEST_PRECEDENCE} so the id is available to
 * every other filter in the chain; only this filter's own MDC key is removed in {@code finally}, so
 * other MDC entries are never disturbed and nothing leaks into the next request handled by the
 * servlet container's thread.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class CorrelationIdFilter implements Filter {

  private static final String HEADER = "X-Correlation-ID";

  /** MDC key; matches the observability standard's {@code request_id} field name. */
  public static final String MDC_KEY = "request_id";

  private static final Pattern VALID_ID = Pattern.compile("[A-Za-z0-9._-]{1,64}");

  /**
   * Resolves or generates the request id, exposes it via MDC and the response header for the
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
    String requestId = httpRequest.getHeader(HEADER);
    if (requestId == null || !VALID_ID.matcher(requestId).matches()) {
      requestId = UUID.randomUUID().toString();
    }
    try {
      MDC.put(MDC_KEY, requestId);
      httpResponse.setHeader(HEADER, requestId);
      chain.doFilter(request, response);
    } finally {
      MDC.remove(MDC_KEY);
    }
  }
}
