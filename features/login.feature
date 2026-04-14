Feature: Login

  Scenario: Successful login with valid credentials
    Given I am on the login page
    When I enter username "standard_user" and password "secret_sauce"
    And I click the login button
    Then I should see a welcome message

  Scenario: Failed login with invalid credentials
    Given I am on the login page
    When I enter username "locked_out_user" and password "wrong_password"
    And I click the login button
    Then I should see an error message "Invalid username or password"
