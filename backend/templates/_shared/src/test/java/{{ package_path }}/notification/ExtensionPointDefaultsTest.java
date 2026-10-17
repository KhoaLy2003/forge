package {{ base_package }}.notification;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ExtensionPointDefaultsTest {

  @Test
  void defaultRecipientDirectory_findsNobody() {
    assertThat(RecipientDirectory.NONE.find(UUID.randomUUID())).isEmpty();
  }

  @Test
  void defaultCurrentRecipientProvider_hasNoCaller() {
    assertThat(CurrentRecipientProvider.NONE.currentRecipientId()).isEmpty();
  }

  @Test
  void aProjectCanImplementTheInterfacesWithALambda() {
    UUID id = UUID.randomUUID();
    RecipientDirectory directory = recipientId -> Optional.of(new Recipient("a@b.c", "en"));
    CurrentRecipientProvider provider = () -> Optional.of(id);

    assertThat(directory.find(UUID.randomUUID())).contains(new Recipient("a@b.c", "en"));
    assertThat(provider.currentRecipientId()).contains(id);
  }

  @Test
  void sendOutcome_factoriesDescribeEachResult() {
    assertThat(ChannelSender.SendOutcome.sent("m-1").result()).isEqualTo(ChannelSender.Result.SENT);
    assertThat(ChannelSender.SendOutcome.sent("m-1").providerMessageId()).isEqualTo("m-1");
    assertThat(ChannelSender.SendOutcome.sent(null).providerMessageId()).isNull();
    assertThat(ChannelSender.SendOutcome.notConfigured().result())
        .isEqualTo(ChannelSender.Result.NOT_CONFIGURED);
    assertThat(ChannelSender.SendOutcome.failed().result()).isEqualTo(ChannelSender.Result.FAILED);
  }
}
