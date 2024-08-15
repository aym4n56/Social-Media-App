describe('Signup and Login Flow', () => {
    it('allows a user to sign up and redirects to the login page', () => {
      // Visit the signup page
      cy.visit('http://127.0.0.1:5000')
  
      // Fill out the signup form
      cy.get('#name').type('Test User')
      cy.get('#email').type('testuser@example.com')
      cy.get('#password').type('password123')
      cy.get('#password_confirmation').type('password123')
  
      // Submit the form
      cy.get('form').submit()
  
      // Verify redirection to the login page
      cy.url().should('include', '/login')
    })
  })
  