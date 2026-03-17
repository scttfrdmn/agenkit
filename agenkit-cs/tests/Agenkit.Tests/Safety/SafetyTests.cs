using Agenkit.Core;
using Agenkit.Safety;

namespace Agenkit.Tests.Safety;

public class InputValidatorTests
{
    [Fact]
    public void Validate_WithinMaxLength_Passes()
    {
        var v = InputValidator.WithMaxLength(100);
        var result = v.Validate(Message.NewMessage("user", "hello"));
        result.IsValid.Should().BeTrue();
    }

    [Fact]
    public void Validate_ExceedsMaxLength_Fails()
    {
        var v = InputValidator.WithMaxLength(5);
        var result = v.Validate(Message.NewMessage("user", "this is way too long"));
        result.IsValid.Should().BeFalse();
        result.Error.Should().Contain("maximum");
    }

    [Fact]
    public void Validate_BlocklistedTerm_Fails()
    {
        var v = InputValidator.WithBlocklist(new[] { "badword" });
        var result = v.Validate(Message.NewMessage("user", "contains badword inside"));
        result.IsValid.Should().BeFalse();
    }

    [Fact]
    public void Validate_BlocklistCaseInsensitive_Fails()
    {
        var v = InputValidator.WithBlocklist(new[] { "badword" });
        var result = v.Validate(Message.NewMessage("user", "BADWORD"));
        result.IsValid.Should().BeFalse();
    }

    [Fact]
    public void ValidationResult_Ok_IsValid()
    {
        ValidationResult.Ok.IsValid.Should().BeTrue();
        ValidationResult.Ok.Error.Should().BeNull();
    }

    [Fact]
    public void ValidationResult_Fail_IsNotValid()
    {
        var r = ValidationResult.Fail("error");
        r.IsValid.Should().BeFalse();
        r.Error.Should().Be("error");
    }
}

public class OutputValidatorTests
{
    [Fact]
    public void RequireNonEmpty_WithContent_Passes()
    {
        var v = OutputValidator.RequireNonEmpty();
        var result = v.Validate(Message.NewMessage("assistant", "response"));
        result.IsValid.Should().BeTrue();
    }

    [Fact]
    public void RequireNonEmpty_EmptyContent_Fails()
    {
        var v = OutputValidator.RequireNonEmpty();
        var result = v.Validate(Message.NewMessage("assistant", ""));
        result.IsValid.Should().BeFalse();
    }

    [Fact]
    public void RequireAssistantRole_AssistantRole_Passes()
    {
        var v = OutputValidator.RequireAssistantRole();
        var result = v.Validate(Message.NewMessage("assistant", "ok"));
        result.IsValid.Should().BeTrue();
    }

    [Fact]
    public void RequireAssistantRole_WrongRole_Fails()
    {
        var v = OutputValidator.RequireAssistantRole();
        var result = v.Validate(Message.NewMessage("user", "oops"));
        result.IsValid.Should().BeFalse();
    }
}

public class AnomalyDetectorTests
{
    [Fact]
    public void Analyze_NormalMessage_NoAnomalies()
    {
        var detector = new AnomalyDetector();
        var anomalies = detector.Analyze(Message.NewMessage("user", "normal message here"));
        anomalies.Should().BeEmpty();
    }

    [Fact]
    public void Analyze_LongMessage_DetectsAnomaly()
    {
        var detector = new AnomalyDetector(maxContentLength: 10);
        var anomalies = detector.Analyze(Message.NewMessage("user", "this message is too long"));
        anomalies.Should().ContainSingle(a => a.Contains("length"));
    }

    [Fact]
    public void Analyze_HighRepetition_DetectsAnomaly()
    {
        var detector = new AnomalyDetector(maxRepetitionRatio: 50);
        var anomalies = detector.Analyze(Message.NewMessage("user", new string('a', 100)));
        anomalies.Should().ContainSingle(a => a.Contains("repetition"));
    }

    [Fact]
    public void Analyze_SuspiciousPattern_DetectsAnomaly()
    {
        var detector = new AnomalyDetector(suspiciousPatterns: new[] { "INJECTION" });
        var anomalies = detector.Analyze(Message.NewMessage("user", "SQL INJECTION attempt"));
        anomalies.Should().ContainSingle(a => a.Contains("INJECTION"));
    }

    [Fact]
    public void IsAnomalous_CleanMessage_ReturnsFalse()
    {
        var detector = new AnomalyDetector();
        detector.IsAnomalous(Message.NewMessage("user", "hi there")).Should().BeFalse();
    }
}

public class PermissionCheckerTests
{
    [Fact]
    public void HasPermission_WithGrantedPermission_ReturnsTrue()
    {
        var checker = new PermissionChecker();
        checker.Grant("user", "read");
        checker.HasPermission("user", "read").Should().BeTrue();
    }

    [Fact]
    public void HasPermission_WithoutPermission_ReturnsFalse()
    {
        var checker = new PermissionChecker();
        checker.HasPermission("user", "write").Should().BeFalse();
    }

    [Fact]
    public void HasPermission_WildcardRole_ReturnsTrue()
    {
        var checker = new PermissionChecker();
        checker.Grant("admin", "*");
        checker.HasPermission("admin", "anything").Should().BeTrue();
    }

    [Fact]
    public void Require_WithPermission_DoesNotThrow()
    {
        var checker = new PermissionChecker();
        checker.Grant("user", "read");
        checker.Invoking(c => c.Require(Message.NewMessage("user", "test"), "read"))
            .Should().NotThrow();
    }

    [Fact]
    public void Require_WithoutPermission_ThrowsUnauthorized()
    {
        var checker = new PermissionChecker();
        checker.Invoking(c => c.Require(Message.NewMessage("user", "test"), "write"))
            .Should().Throw<UnauthorizedAccessException>();
    }
}
