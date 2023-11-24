from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.forms import formset_factory
from django.contrib import messages


from .forms import PurchaseItemForm

from django.views.generic import (
    View, 
    ListView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import (
    PurchaseBill, 
    Supplier, 
    PurchaseItem,
    PurchaseBillDetails,
    SaleBill,  
    SaleItem,
    SaleBillDetails
)
from .forms import (
    SelectSupplierForm, 
    PurchaseItemFormset,
    PurchaseDetailsForm, 
    SupplierForm, 
    SaleForm,
    SaleItemFormset,
    SaleDetailsForm
)
from inventory.models import Stock




# shows a lists of all suppliers
class SupplierListView(ListView):
    model = Supplier
    template_name = "suppliers/suppliers_list.html"
    queryset = Supplier.objects.filter(is_deleted=False)
    paginate_by = 10


# used to add a new supplier
class SupplierCreateView(SuccessMessageMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    success_url = '/transactions/suppliers'
    success_message = "Supplier has been created successfully"
    template_name = "suppliers/edit_supplier.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = 'New Supplier'
        context["savebtn"] = 'Add Supplier'
        return context     


# used to update a supplier's info
class SupplierUpdateView(SuccessMessageMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    success_url = '/transactions/suppliers'
    success_message = "Supplier details has been updated successfully"
    template_name = "suppliers/edit_supplier.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = 'Edit Supplier'
        context["savebtn"] = 'Save Changes'
        context["delbtn"] = 'Delete Supplier'
        return context


# used to delete a supplier
class SupplierDeleteView(View):
    template_name = "suppliers/delete_supplier.html"
    success_message = "Supplier has been deleted successfully"

    def get(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        return render(request, self.template_name, {'object' : supplier})

    def post(self, request, pk):  
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.is_deleted = True
        supplier.save()                                               
        messages.success(request, self.success_message)
        return redirect('suppliers-list')


# used to view a supplier's profile
class SupplierView(View):
    def get(self, request, name):
        supplierobj = get_object_or_404(Supplier, name=name)
        bill_list = PurchaseBill.objects.filter(supplier=supplierobj)
        page = request.GET.get('page', 1)
        paginator = Paginator(bill_list, 10)
        try:
            bills = paginator.page(page)
        except PageNotAnInteger:
            bills = paginator.page(1)
        except EmptyPage:
            bills = paginator.page(paginator.num_pages)
        context = {
            'supplier'  : supplierobj,
            'bills'     : bills
        }
        return render(request, 'suppliers/supplier.html', context)




# shows the list of bills of all purchases 
class PurchaseView(ListView):
    model = PurchaseBill
    template_name = "purchases/purchases_list.html"
    context_object_name = 'bills'
    ordering = ['-time']
    paginate_by = 10


# used to select the supplier
class SelectSupplierView(View):
    form_class = SelectSupplierForm
    template_name = 'purchases/select_supplier.html'

    def get(self, request, *args, **kwargs):                                    # loads the form page
        form = self.form_class
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):                                   # gets selected supplier and redirects to 'PurchaseCreateView' class
        form = self.form_class(request.POST)
        if form.is_valid():
            supplierid = request.POST.get("supplier")
            supplier = get_object_or_404(Supplier, id=supplierid)
            return redirect('new-purchase', supplier.pk)
        return render(request, self.template_name, {'form': form})

# views.py


def get_stock_perprice(request, stock_id):
    stock = get_object_or_404(Stock, id=stock_id)

    # Assuming your Stock model has a 'price' field
    perprice = stock.price

    return JsonResponse({'perprice': perprice})





class PurchaseCreateView(View):
    template_name = 'purchases/new_purchase.html'

    def calculate_grand_total(self, purchase_items):
        grand_total = 0
        for item in purchase_items:
            grand_total += item.net_amount
        return grand_total

    def get(self, request, pk):
        formset = PurchaseItemFormset(request.GET or None)
        hes = Stock.objects.all()
        stock_prices = {stock.id: stock.price for stock in Stock.objects.all()}

        supplierobj = get_object_or_404(Supplier, pk=pk)
        context = {
            'formset': formset,
            'supplier': supplierobj,
            'hes': hes,
            'stock_prices': stock_prices,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        purchase_items = []
        formset = PurchaseItemFormset(request.POST)
        supplierobj = get_object_or_404(Supplier, pk=pk)

        if formset.is_valid():
            with transaction.atomic():
                billobj = PurchaseBill(supplier=supplierobj)
                billobj.save()

                billdetailsobj = PurchaseBillDetails(billno=billobj)
                billdetailsobj.save()

                grand_total = 0

                for form in formset:
                    purchaseitem = form.save(commit=False)
                    purchaseitem.billno = billobj

                    stock = get_object_or_404(Stock, name=purchaseitem.stock)
                    x=stock.price

                    # Automatically set perprice based on the selected stock's price
                    purchaseitem.perprice = stock.price
                    

                    purchaseitem.save()

                    purchaseitem.totalprice = purchaseitem.perprice * purchaseitem.quantity

                    # Simplified net_amount calculation
                    purchaseitem.net_amount = purchaseitem.totalprice * (1 - purchaseitem.discount / 100)

                    stock.quantity += purchaseitem.quantity
                    stock.save()

                    grand_total += purchaseitem.net_amount

                    purchase_items.append(purchaseitem)
                    purchaseitem.grand_total = self.calculate_grand_total(purchase_items)
                    purchaseitem.save()

                billobj.grand_total = grand_total
                billobj.save()

                # Calculate perprices for each stock and send them as JSON response
                stock_perprices = {stock.id: stock.price for stock in Stock.objects.all()}
                return redirect('purchase-bill', billno=billobj.billno)

        formset = PurchaseItemFormset(request.GET or None)
        context = {
            'formset': formset,
            'supplier': supplierobj
        }
        return render(request, self.template_name, context)

# Create a PurchaseItem formset with the PurchaseItemForm
PurchaseItemFormset = formset_factory(PurchaseItemForm, extra=1)

# ... (your existing code)


# used to delete a bill object
class PurchaseDeleteView(SuccessMessageMixin, DeleteView):
    model = PurchaseBill
    template_name = "purchases/delete_purchase.html"
    success_url = '/transactions/purchases'
    
    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        items = PurchaseItem.objects.filter(billno=self.object.billno)
        for item in items:
            stock = get_object_or_404(Stock, name=item.stock.name)
            if stock.is_deleted == False:
                stock.quantity -= item.quantity
                stock.save()
        messages.success(self.request, "Purchase bill has been deleted successfully")
        return super(PurchaseDeleteView, self).delete(*args, **kwargs)




# shows the list of bills of all sales 
class SaleView(ListView):
    model = SaleBill
    template_name = "sales/sales_list.html"
    context_object_name = 'bills'
    ordering = ['-time']
    paginate_by = 10


# used to generate a bill object and save items
class SaleCreateView(View):
    template_name = 'sales/new_sale.html'

    def calculate_grand_total(self, sale_items):
        grand_total = 0
        for item in sale_items:
            grand_total += item.net_amount
        return grand_total

    def get(self, request):
        form = SaleForm(request.GET or None)
        formset = PurchaseItemFormset(request.GET or None)
        hes = Stock.objects.all()
        stock_prices = {stock.id: stock.price for stock in Stock.objects.all()}

        context = {
            'form': form,
            'formset': formset,
            'stock_prices': stock_prices,
            'hes': hes,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        sale_items = []   
        form = SaleForm(request.POST)
        formset = SaleItemFormset(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                billobj = form.save(commit=False)
                billobj.save()

                billdetailsobj = SaleBillDetails(billno=billobj)
                billdetailsobj.save()

                grand_total = 0

                for form in formset:
                    billitem = form.save(commit=False)
                    billitem.billno = billobj

                    stock = get_object_or_404(Stock, name=billitem.stock.name)
                    billitem.totalprice = billitem.perprice * billitem.quantity

                    # Calculate and set discounted price
                    quantity = form.cleaned_data.get('quantity')
                    price = form.cleaned_data.get('perprice')
                    discount = form.cleaned_data.get('discount')
                    net_amount = price - (price * (discount / 100))
                    form.cleaned_data['discounted_price'] = net_amount
                    billitem.net_amount = net_amount

                    stock.quantity -= quantity
                    stock.save()

                   

                    grand_total += billitem.net_amount

                    sale_items.append(billitem)
                    billitem.grand_total = self.calculate_grand_total(sale_items)
                    # billobj.save()
                    billitem.save()

            # Calculate and set billobj.grand_total outside the transaction block
           

            messages.success(request, "Sold items have been registered successfully")
            return redirect('sale-bill', billno=billobj.billno)

        form = SaleForm(request.GET or None)
        formset = SaleItemFormset(request.GET or None)
        context = {
            'form': form,
            'formset': formset,
        }
        return render(request, self.template_name, context)
# used to delete a bill object
class SaleDeleteView(SuccessMessageMixin, DeleteView):
    model = SaleBill
    template_name = "sales/delete_sale.html"
    success_url = '/transactions/sales'
    
    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        items = SaleItem.objects.filter(billno=self.object.billno)
        for item in items:
            stock = get_object_or_404(Stock, name=item.stock.name)
            if stock.is_deleted == False:
                stock.quantity += item.quantity
                stock.save()
        messages.success(self.request, "Sale bill has been deleted successfully")
        return super(SaleDeleteView, self).delete(*args, **kwargs)


# used to display the purchase bill object
class PurchaseBillView(View):
    model = PurchaseBill
    template_name = "bill/purchase_bill.html"
    bill_base = "bill/bill_base.html"

    def get(self, request, billno):
        context = {
            'bill'          : PurchaseBill.objects.get(billno=billno),
            'items'         : PurchaseItem.objects.filter(billno=billno),
            'billdetails'   : PurchaseBillDetails.objects.get(billno=billno),
            'bill_base'     : self.bill_base,
        }
        return render(request, self.template_name, context)

    def post(self, request, billno):
        form = PurchaseDetailsForm(request.POST)
        if form.is_valid():
            billdetailsobj = PurchaseBillDetails.objects.get(billno=billno)
            
            billdetailsobj.eway = request.POST.get("eway")    
            billdetailsobj.veh = request.POST.get("veh")
            billdetailsobj.destination = request.POST.get("destination")
            billdetailsobj.po = request.POST.get("po")
            billdetailsobj.cgst = request.POST.get("cgst")
            billdetailsobj.sgst = request.POST.get("sgst")
            billdetailsobj.igst = request.POST.get("igst")
            billdetailsobj.cess = request.POST.get("cess")
            billdetailsobj.tcs = request.POST.get("tcs")
            billdetailsobj.total = request.POST.get("total")

            billdetailsobj.save()
            messages.success(request, "Bill details have been modified successfully")
        context = {
            'bill'          : PurchaseBill.objects.get(billno=billno),
            'items'         : PurchaseItem.objects.filter(billno=billno),
            'billdetails'   : PurchaseBillDetails.objects.get(billno=billno),
            'bill_base'     : self.bill_base,
        }
        return render(request, self.template_name, context)


# used to display the sale bill object
class SaleBillView(View):
    model = SaleBill
    template_name = "bill/sale_bill.html"
    bill_base = "bill/bill_base.html"
    
    def get(self, request, billno):
        context = {
            'bill'          : SaleBill.objects.get(billno=billno),
            'items'         : SaleItem.objects.filter(billno=billno),
            'billdetails'   : SaleBillDetails.objects.get(billno=billno),
            'bill_base'     : self.bill_base,
        }
        return render(request, self.template_name, context)

    def post(self, request, billno):
        form = SaleDetailsForm(request.POST)
        if form.is_valid():
            billdetailsobj = SaleBillDetails.objects.get(billno=billno)
            
            billdetailsobj.eway = request.POST.get("eway")    
            billdetailsobj.veh = request.POST.get("veh")
            billdetailsobj.destination = request.POST.get("destination")
            billdetailsobj.po = request.POST.get("po")
            billdetailsobj.cgst = request.POST.get("cgst")
            billdetailsobj.sgst = request.POST.get("sgst")
            billdetailsobj.igst = request.POST.get("igst")
            billdetailsobj.cess = request.POST.get("cess")
            billdetailsobj.tcs = request.POST.get("tcs")
            billdetailsobj.total = request.POST.get("total")

            billdetailsobj.save()
            messages.success(request, "Bill details have been modified successfully")
        context = {
            'bill'          : SaleBill.objects.get(billno=billno),
            'items'         : SaleItem.objects.filter(billno=billno),
            'billdetails'   : SaleBillDetails.objects.get(billno=billno),
            'bill_base'     : self.bill_base,
        }
        return render(request, self.template_name, context)