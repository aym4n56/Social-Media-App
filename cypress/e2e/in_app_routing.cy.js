describe('Login and Route to pages', () => {
    it('allows a user to log in and redirects to the home page', () => {
      // Visit the login page
      cy.visit('http://127.0.0.1:5000/login')
  
      // Fill out the login form
      cy.get('#email').type('testuser@example.com')
      cy.get('#password').type('password123')
  
      // Submit the form
      cy.get('form').submit()
  
      // Verify redirection to the home page
      cy.url().should('include', '/home')
      cy.contains('Welcome') // Check if a welcome message or any content in home.html is visible
      
      cy.contains('Welcome');

      // Click on the "Friends" link in the navbar
      cy.get('.navbar a').contains('Friends').click();
      cy.url().should('include', '/friends');

      cy.get('.navbar a').contains('Feed').click();
      cy.url().should('include', '/feed');

      cy.get('.navbar a').contains('Profile').click();
      cy.url().should('include', '/profile')
      
    })
  })
  