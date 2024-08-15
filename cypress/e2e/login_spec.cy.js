describe('Login Flow', () => {
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
    })
  })
  