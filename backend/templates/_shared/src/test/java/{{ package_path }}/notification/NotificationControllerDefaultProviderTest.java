package {{ base_package }}.notification;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import {{ base_package }}.common.exception.GlobalExceptionHandler;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * A freshly generated project defines no {@link CurrentRecipientProvider}: the inbox API must
 * answer 401 rather than fail to start or guess a caller.
 */
@WebMvcTest(NotificationController.class)
@Import(GlobalExceptionHandler.class)
@AutoConfigureMockMvc(addFilters = false)
class NotificationControllerDefaultProviderTest {

  @Autowired private MockMvc mockMvc;

  @MockitoBean private NotificationService service;

  @Test
  void withoutAProviderBeanTheApiAnswers401() throws Exception {
    mockMvc
        .perform(get("/api/v1/notifications"))
        .andExpect(status().isUnauthorized())
        .andExpect(jsonPath("$.data.code").value("UNAUTHORIZED"));

    verifyNoInteractions(service);
  }
}
