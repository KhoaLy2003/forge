package {{ base_package }}.common.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.slf4j.MDC;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class CorrelationIdFilterTest {

  private static final String HEADER = "X-Correlation-ID";
  private static final String MDC_KEY = CorrelationIdFilter.MDC_KEY;

  @AfterEach
  void cleanMdc() {
    MDC.clear();
  }

  private static MockFilterChain capturing(AtomicReference<String> captured) {
    return new MockFilterChain() {
      @Override
      public void doFilter(ServletRequest req, ServletResponse res)
          throws IOException, ServletException {
        captured.set(MDC.get(MDC_KEY));
        super.doFilter(req, res);
      }
    };
  }

  @Test
  void mdcKeyMatchesTheStandardsRequestIdField() {
    assertThat(MDC_KEY).isEqualTo("request_id");
  }

  @Test
  void doFilter_withNoIncomingHeader_generatesAndEchoesRequestId() throws Exception {
    MockHttpServletResponse response = new MockHttpServletResponse();
    AtomicReference<String> captured = new AtomicReference<>();

    new CorrelationIdFilter().doFilter(new MockHttpServletRequest(), response, capturing(captured));

    assertThat(captured.get()).isNotBlank();
    assertThat(response.getHeader(HEADER)).isEqualTo(captured.get());
  }

  @Test
  void doFilter_withValidIncomingHeader_reusesIt() throws Exception {
    MockHttpServletRequest request = new MockHttpServletRequest();
    request.addHeader(HEADER, "test-id_123.abc");
    MockHttpServletResponse response = new MockHttpServletResponse();
    AtomicReference<String> captured = new AtomicReference<>();

    new CorrelationIdFilter().doFilter(request, response, capturing(captured));

    assertThat(captured.get()).isEqualTo("test-id_123.abc");
    assertThat(response.getHeader(HEADER)).isEqualTo("test-id_123.abc");
  }

  @Test
  void doFilter_withMaximumLengthHeader_reusesIt() throws Exception {
    String id = "a".repeat(64);
    MockHttpServletRequest request = new MockHttpServletRequest();
    request.addHeader(HEADER, id);
    MockHttpServletResponse response = new MockHttpServletResponse();

    new CorrelationIdFilter().doFilter(request, response, new MockFilterChain());

    assertThat(response.getHeader(HEADER)).isEqualTo(id);
  }

  @ParameterizedTest
  @ValueSource(
      strings = {
        "",
        "   ",
        "has space",
        "line\r\nbreak",
        "{\"fake\":true}",
        "semi;colon",
        "tab\there"
      })
  void doFilter_withMalformedHeader_replacesItWithGeneratedId(String bad) throws Exception {
    MockHttpServletRequest request = new MockHttpServletRequest();
    request.addHeader(HEADER, bad);
    MockHttpServletResponse response = new MockHttpServletResponse();
    AtomicReference<String> captured = new AtomicReference<>();

    new CorrelationIdFilter().doFilter(request, response, capturing(captured));

    assertThat(captured.get()).isNotEqualTo(bad).matches("[A-Za-z0-9._-]{1,64}");
    assertThat(response.getHeader(HEADER)).isEqualTo(captured.get());
  }

  @Test
  void doFilter_withTooLongHeader_replacesIt() throws Exception {
    String tooLong = "a".repeat(65);
    MockHttpServletRequest request = new MockHttpServletRequest();
    request.addHeader(HEADER, tooLong);
    MockHttpServletResponse response = new MockHttpServletResponse();

    new CorrelationIdFilter().doFilter(request, response, new MockFilterChain());

    assertThat(response.getHeader(HEADER)).isNotEqualTo(tooLong);
  }

  @Test
  void doFilter_removesOnlyItsOwnMdcKeyAfterChainCompletes() throws Exception {
    MDC.put("job", "keep-me");

    new CorrelationIdFilter()
        .doFilter(
            new MockHttpServletRequest(), new MockHttpServletResponse(), new MockFilterChain());

    assertThat(MDC.get(MDC_KEY)).isNull();
    assertThat(MDC.get("job")).isEqualTo("keep-me");
  }

  @Test
  void doFilter_removesItsMdcKeyEvenWhenTheChainThrows() {
    MockFilterChain failing =
        new MockFilterChain() {
          @Override
          public void doFilter(ServletRequest req, ServletResponse res) throws ServletException {
            throw new ServletException("boom");
          }
        };

    assertThatThrownBy(
            () ->
                new CorrelationIdFilter()
                    .doFilter(new MockHttpServletRequest(), new MockHttpServletResponse(), failing))
        .isInstanceOf(ServletException.class);

    assertThat(MDC.get(MDC_KEY)).isNull();
  }
}
