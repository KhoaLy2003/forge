package {{ base_package }}.common.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class CorrelationIdFilterTest {

  private static final String HEADER = "X-Correlation-ID";
  private static final String MDC_KEY = "correlationId";

  @Test
  void doFilter_withNoIncomingHeader_generatesAndEchoesCorrelationId() throws Exception {
    MockHttpServletRequest request = new MockHttpServletRequest();
    MockHttpServletResponse response = new MockHttpServletResponse();
    AtomicReference<String> capturedMdcValue = new AtomicReference<>();
    MockFilterChain chain =
        new MockFilterChain() {
          @Override
          public void doFilter(
              jakarta.servlet.ServletRequest req, jakarta.servlet.ServletResponse res)
              throws IOException, jakarta.servlet.ServletException {
            capturedMdcValue.set(MDC.get(MDC_KEY));
            super.doFilter(req, res);
          }
        };

    new CorrelationIdFilter().doFilter(request, response, chain);

    assertThat(capturedMdcValue.get()).isNotNull();
    assertThat(response.getHeader(HEADER)).isEqualTo(capturedMdcValue.get());
  }

  @Test
  void doFilter_withIncomingHeader_reusesIt() throws Exception {
    MockHttpServletRequest request = new MockHttpServletRequest();
    request.addHeader(HEADER, "test-id-123");
    MockHttpServletResponse response = new MockHttpServletResponse();
    MockFilterChain chain = new MockFilterChain();

    new CorrelationIdFilter().doFilter(request, response, chain);

    assertThat(response.getHeader(HEADER)).isEqualTo("test-id-123");
  }

  @Test
  void doFilter_clearsMdcAfterChainCompletes() throws Exception {
    MockHttpServletRequest request = new MockHttpServletRequest();
    MockHttpServletResponse response = new MockHttpServletResponse();
    MockFilterChain chain = new MockFilterChain();

    new CorrelationIdFilter().doFilter(request, response, chain);

    assertThat(MDC.get(MDC_KEY)).isNull();
  }
}
