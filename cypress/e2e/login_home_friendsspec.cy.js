describe('Login and Route to pages', () => {
    it('allows a user to log in and redirects to the home page', () => {
      // Visit the login page
      cy.visit('http://127.0.0.1:5001/login')
  
      // Fill out the login form
      cy.get('#email').type('testuser@example.com')
      cy.get('#password').type('password123')
  
      // Submit the form
      cy.get('form').submit()
  
      // Verify redirection to the home page
      cy.url().should('include', '/home')
      cy.contains('Welcome') // Check if a welcome message or any content in home.html is visible
      
      cy.contains('Welcome to PinTip');

      // Click on the "Friends" link in the navbar
      cy.get('.navbar a').contains('Friends').click();

      // Ensure the URL is correct after navigation
      cy.url().should('include', '/friends');

      // Check that the Friends page loads by verifying the presence of a specific element
      cy.contains('Friends Page');

      cy.get('.navbar a').contains('Feed').click();
      cy.url().should('include', '/feed');

      
    })
  })
  