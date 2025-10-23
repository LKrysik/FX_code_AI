http://localhost:3000/indicators

Update Variant,delete variant, load variants

Are variants saved in config folder?

Errors 
Failed to delete variant:
Failed to save variant: 
Failed to load variants

{"type":"error","error_code":"not_found","error_message":"Variant not found: variant-1759258078390","version":"1.0","timestamp":"2025-09-30T20:48:48.581189"}

VariantManager.tsx


Error -> Failed to delete variant
      onVariantDeleted?.(variantId);
    } catch (error: any) {
      console.error('Failed to delete variant:', error);

 
Error -> Failed to save variant
      setDialogOpen(false);
      setSelectedSystemIndicator(null);
      setEditingVariant(null);
    } catch (error: any) {
      console.error('Failed to save variant:', error);
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          'Unknown error occurred';
      setSnackbar({


Error -> Failed to load variants
    } catch (error) {
      console.error('Failed to load variants:', error);
      setVariants([]);
      setSnackbar({



INFO:     127.0.0.1:52094 - "GET /variants HTTP/1.1" 400 Bad Request
INFO:     127.0.0.1:64367 - "GET /variants?type=take_profit HTTP/1.1" 400 Bad Request
INFO:     127.0.0.1:64367 - "GET /variants HTTP/1.1" 400 Bad Request
INFO:     127.0.0.1:64367 - "GET /variants?type=take_profit HTTP/1.1" 400 Bad Request
INFO:     127.0.0.1:64225 - "PUT /variants/variant-1759258411920 HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:60010 - "DELETE /variants/variant-1759258411920 HTTP/1.1" 404 Not Found