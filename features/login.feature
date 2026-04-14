Feature: User Login

  Scenario Outline: User can log in with valid credentials
    Given the user is on the login page
    When the user enters username "<username>" and password "<password>"
    Then the user should be redirected to the dashboard

    Examples:
      | username  | password             |
      | tomsmith  | SuperSecretPassword! |

  Scenario Outline: User cannot log in with invalid credentials
    Given the user is on the login page
    When the user enters username "<username>" and password "<password>"
    Then an error message should be displayed

    Examples:
      | username  | password    |
      | testuser  | password123 |
      | baduser   | wrongpass   |