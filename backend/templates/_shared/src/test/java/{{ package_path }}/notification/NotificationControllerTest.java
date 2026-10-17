package {{ base_package }}.notification;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.common.dto.PaginationMeta;
import {{ base_package }}.common.exception.GlobalExceptionHandler;
import {{ base_package }}.common.exception.ResourceNotFoundException;
import {{ base_package }}.notification.dto.InboxItemResponse;
import {{ base_package }}.notification.dto.PreferencesResponse;
import {{ base_package }}.notification.dto.UpdatePreferencesRequest;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Stream;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

@WebMvcTest(NotificationController.class)
@Import(GlobalExceptionHandler.class)
@AutoConfigureMockMvc(addFilters = false)
class NotificationControllerTest {

  @Autowired private MockMvc mockMvc;

  @MockitoBean private NotificationService service;

  @MockitoBean private CurrentRecipientProvider currentRecipient;

  private final UUID caller = UUID.randomUUID();

  @BeforeEach
  void authenticate() {
    when(currentRecipient.currentRecipientId()).thenReturn(Optional.of(caller));
  }

  private static InboxItemResponse item(String title) {
    return new InboxItemResponse(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "WELCOME",
        title,
        "body of " + title,
        Instant.parse("2026-01-01T00:00:00Z"),
        false);
  }

  // ------------------------------------------------------------------- inbox

  @Test
  void list_returnsTheCallersInboxInTheStandardEnvelope() throws Exception {
    PaginationMeta meta = PaginationMeta.builder().page(0).limit(20).total(1).totalPages(1).build();
    when(service.inbox(caller, 0, 20))
        .thenReturn(
            PageResponse.<InboxItemResponse>builder()
                .data(List.of(item("Hi")))
                .pagination(meta)
                .build());

    mockMvc
        .perform(get("/api/v1/notifications"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.success").value(true))
        .andExpect(jsonPath("$.data.data[0].title").value("Hi"))
        .andExpect(jsonPath("$.data.data[0].read").value(false))
        .andExpect(jsonPath("$.data.pagination.total").value(1));
  }

  @Test
  void list_passesPageAndSizeThrough() throws Exception {
    when(service.inbox(caller, 2, 5))
        .thenReturn(
            PageResponse.<InboxItemResponse>builder()
                .data(List.of())
                .pagination(new PaginationMeta())
                .build());

    mockMvc
        .perform(get("/api/v1/notifications").param("page", "2").param("size", "5"))
        .andExpect(status().isOk());

    verify(service).inbox(caller, 2, 5);
  }

  @ParameterizedTest
  @MethodSource("invalidPaging")
  void list_rejectsOutOfRangePaging(String page, String size) throws Exception {
    mockMvc
        .perform(get("/api/v1/notifications").param("page", page).param("size", size))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.success").value(false));

    verify(service, never()).inbox(any(), anyInt(), anyInt());
  }

  static Stream<org.junit.jupiter.params.provider.Arguments> invalidPaging() {
    return Stream.of(
        org.junit.jupiter.params.provider.Arguments.of("0", "0"),
        org.junit.jupiter.params.provider.Arguments.of("0", "101"),
        org.junit.jupiter.params.provider.Arguments.of("-1", "20"));
  }

  @Test
  void list_ignoresARecipientIdSuppliedByTheClient() throws Exception {
    UUID someoneElse = UUID.randomUUID();
    when(service.inbox(any(), anyInt(), anyInt()))
        .thenReturn(
            PageResponse.<InboxItemResponse>builder()
                .data(List.of())
                .pagination(new PaginationMeta())
                .build());

    mockMvc
        .perform(
            get("/api/v1/notifications")
                .param("recipientId", someoneElse.toString())
                .param("userId", someoneElse.toString())
                .header("X-Recipient-Id", someoneElse.toString()))
        .andExpect(status().isOk());

    verify(service).inbox(eq(caller), anyInt(), anyInt());
    verify(service, never()).inbox(eq(someoneElse), anyInt(), anyInt());
  }

  @Test
  void unreadCount_returnsTheCount() throws Exception {
    when(service.unreadCount(caller)).thenReturn(3L);

    mockMvc
        .perform(get("/api/v1/notifications/unread-count"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.data.count").value(3));
  }

  // -------------------------------------------------------- read and dismiss

  @Test
  void markRead_returns204AndMarksTheCallersDelivery() throws Exception {
    UUID delivery = UUID.randomUUID();

    mockMvc
        .perform(patch("/api/v1/notifications/{id}/read", delivery))
        .andExpect(status().isNoContent());

    verify(service).markRead(caller, delivery);
  }

  @Test
  void markRead_ofSomeoneElsesDelivery_is404() throws Exception {
    UUID delivery = UUID.randomUUID();
    doThrow(new ResourceNotFoundException("Notification not found: " + delivery))
        .when(service)
        .markRead(caller, delivery);

    mockMvc
        .perform(patch("/api/v1/notifications/{id}/read", delivery))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.success").value(false));
  }

  @Test
  void readAll_returns204() throws Exception {
    mockMvc.perform(post("/api/v1/notifications/read-all")).andExpect(status().isNoContent());

    verify(service).markAllRead(caller);
  }

  @Test
  void delete_returns204AndDismissesTheCallersDelivery() throws Exception {
    UUID delivery = UUID.randomUUID();

    mockMvc
        .perform(delete("/api/v1/notifications/{id}", delivery))
        .andExpect(status().isNoContent());

    verify(service).deleteNotification(caller, delivery);
  }

  @Test
  void delete_ofAnUnknownDelivery_is404() throws Exception {
    UUID delivery = UUID.randomUUID();
    doThrow(new ResourceNotFoundException("Notification not found: " + delivery))
        .when(service)
        .deleteNotification(caller, delivery);

    mockMvc
        .perform(delete("/api/v1/notifications/{id}", delivery))
        .andExpect(status().isNotFound());
  }

  // ------------------------------------------------------------- preferences

  @Test
  void getPreferences_returnsTheCallersPreferences() throws Exception {
    when(service.getPreferences(caller)).thenReturn(new PreferencesResponse(false));

    mockMvc
        .perform(get("/api/v1/notifications/preferences"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.data.emailEnabled").value(false));
  }

  @Test
  void updatePreferences_appliesThePartialUpdate() throws Exception {
    when(service.updatePreferences(eq(caller), any())).thenReturn(new PreferencesResponse(false));

    mockMvc
        .perform(
            put("/api/v1/notifications/preferences")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"emailEnabled\":false}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.data.emailEnabled").value(false));

    verify(service).updatePreferences(caller, new UpdatePreferencesRequest(false));
  }

  @Test
  void updatePreferences_withAnEmptyBodyObject_changesNothing() throws Exception {
    when(service.updatePreferences(eq(caller), any())).thenReturn(new PreferencesResponse(true));

    mockMvc
        .perform(
            put("/api/v1/notifications/preferences")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
        .andExpect(status().isOk());

    verify(service).updatePreferences(caller, new UpdatePreferencesRequest(null));
  }

  // ----------------------------------------------------- not authenticated

  static Stream<MockHttpServletRequestBuilder> everyEndpoint() {
    UUID id = UUID.randomUUID();
    return Stream.of(
        get("/api/v1/notifications"),
        get("/api/v1/notifications/unread-count"),
        patch("/api/v1/notifications/{id}/read", id),
        post("/api/v1/notifications/read-all"),
        delete("/api/v1/notifications/{id}", id),
        get("/api/v1/notifications/preferences"),
        put("/api/v1/notifications/preferences")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"emailEnabled\":true}"));
  }

  @ParameterizedTest
  @MethodSource("everyEndpoint")
  void everyEndpointAnswers401WhenThereIsNoCaller(MockHttpServletRequestBuilder request)
      throws Exception {
    when(currentRecipient.currentRecipientId()).thenReturn(Optional.empty());

    mockMvc
        .perform(request)
        .andExpect(status().isUnauthorized())
        .andExpect(jsonPath("$.success").value(false))
        .andExpect(jsonPath("$.data.code").value("UNAUTHORIZED"));

    verifyNoInteractions(service);
  }
}
